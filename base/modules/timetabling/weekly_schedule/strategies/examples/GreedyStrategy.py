"""
GreedyStrategy — bulk-tolerant timetable generator.

Key behaviours vs a naive greedy:
  - Round-robin slot selection spreads entries evenly across the week.
  - Two-phase placement: tries strict day-spread cap first, then
    relaxes it automatically per-entry if needed rather than failing.
  - Classes with the most curriculum entries are placed first so they
    get first pick of slots.
  - Lecturer over-subscription is a warning not a failure (necessary
    when the lecturer pool is small relative to class count).
  - Missing professors produce a warning and placement continues.
  - Common units (CC) remain a hard simultaneous-placement constraint.
  - validate() is still called before returning success.

Register in settings.py:
    TIMETABLE_STRATEGY = 'base.modules.timetabling.strategies.greedy.GreedyStrategy'
"""

from collections import defaultdict

from base.modules.timetabling.weekly_schedule.base import (
    AbstractTimetableStrategy,
    TimetableGenerationResult,
    TimetableSlot,
)
from django.conf import settings

config = getattr(settings, 'TIMETABLE_MODULE_CONFIG', {})

DAYS = tuple(day[0] for day in config.get('DAYS',  ()))
SLOTS = tuple(slot[0] for slot in config.get('SLOTS', ()))

# Soft cap — exceeded only when no other slot exists for this class.
MAX_SLOTS_PER_CLASS_PER_DAY = 3


class GreedyStrategy(AbstractTimetableStrategy):

    def generate(self, session) -> TimetableGenerationResult:
        try:
            return self._generate(session)
        except Exception as e:
            return TimetableGenerationResult(
                success=False,
                message=f"Unexpected error during generation: {e}",
            )

    # ─────────────────────────────────────────────────────────────────

    def _generate(self, session) -> TimetableGenerationResult:
        from base.models import Curriculum, Venue

        venues = list(Venue.objects.all())
        if not venues:
            return TimetableGenerationResult(
                success=False,
                message="No venues found. Add venues before generating a timetable.",
            )

        curriculum_qs = (
            Curriculum.objects
            .filter(session=session)
            .select_related('Tclass', 'course')
            .prefetch_related('professor')
        )

        if not curriculum_qs.exists():
            return TimetableGenerationResult(
                success=False,
                message=f"No curriculum entries found for {session}.",
            )

        all_entries = list(curriculum_qs)

        # ── split CC from regular ─────────────────────────────────────
        common_units = defaultdict(list)   # {course_id: [entry, ...]}
        regular = []

        for entry in all_entries:
            if entry.course.course_type == 'CC':
                common_units[entry.course_id].append(entry)
            else:
                regular.append(entry)

        # Sort regular entries: most curricula per class first.
        # This ensures busy classes claim their slots before sparse ones,
        # preventing the "last class has nowhere to go" failure.
        class_load = defaultdict(int)
        for e in regular:
            class_load[e.Tclass.pk] += 1
        regular.sort(key=lambda e: -class_load[e.Tclass.pk])

        # ── booking state (in-memory only) ────────────────────────────
        lecturer_busy = {}   # {(lecturer_id, day, slot): True}
        venue_busy = {}   # {(venue_id,    day, slot): True}
        class_busy = {}   # {(tclass_id,   day, slot): True}
        class_day = defaultdict(int)  # {(tclass_id, day): count}

        all_day_slots = [(d, s) for d in DAYS for s in SLOTS]
        rr_cursor = [0]

        def advance_cursor():
            idx = rr_cursor[0]
            rr_cursor[0] = (idx + 1) % len(all_day_slots)
            return idx

        slots = []
        warnings = []

        # ── place regular courses ─────────────────────────────────────
        for entry in regular:
            professors = list(entry.professor.all())

            if not professors:
                warnings.append(
                    f"{entry.course.course_code} ({entry.Tclass.class_name}) "
                    f"has no assigned professor — placed without lecturer constraint."
                )

            start = advance_cursor()
            placed, w = self._place_with_fallback(
                entries=[entry],
                professors=professors,
                venues=venues,
                lecturer_busy=lecturer_busy,
                venue_busy=venue_busy,
                class_busy=class_busy,
                class_day=class_day,
                slots=slots,
                one_venue_each=False,
                start_idx=start,
            )
            warnings.extend(w)

            if not placed:
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Could not place {entry.course.course_code} "
                        f"for {entry.Tclass.class_name} — all "
                        f"{len(all_day_slots)} day/slot combinations "
                        f"exhausted even after relaxing day-spread limit."
                    ),
                    warnings=warnings,
                )

        # ── place common units ────────────────────────────────────────
        for course_id, entries in common_units.items():
            all_professors = []
            for e in entries:
                all_professors.extend(list(e.professor.all()))

            if not all_professors:
                warnings.append(
                    f"Common unit {entries[0].course.course_code} has no "
                    f"assigned professors — placed without lecturer constraint."
                )

            start = advance_cursor()
            placed, w = self._place_with_fallback(
                entries=entries,
                professors=all_professors,
                venues=venues,
                lecturer_busy=lecturer_busy,
                venue_busy=venue_busy,
                class_busy=class_busy,
                class_day=class_day,
                slots=slots,
                one_venue_each=True,
                start_idx=start,
            )
            warnings.extend(w)

            if not placed:
                code = entries[0].course.course_code
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Could not place common unit {code} — no slot free "
                        f"for all {len(entries)} classes simultaneously."
                    ),
                    warnings=warnings,
                )

        # ── final validation ──────────────────────────────────────────
        result = TimetableGenerationResult(
            success=True,
            slots=slots,
            warnings=warnings,
            message=(
                f"Generated {len(slots)} slot(s) with {len(warnings)} warning(s)."
            ),
            stats={
                'total_slots':  len(slots),
                'common_units': len(common_units),
                'regular':      len(regular),
                'warnings':     len(warnings),
            },
        )

        errors = self.validate(result)
        if errors:
            return TimetableGenerationResult(
                success=False,
                message=f"Validation failed ({len(errors)} error(s)): {errors[0]}",
                warnings=warnings,
            )

        return result

    # ── two-phase placement ───────────────────────────────────────────

    def _place_with_fallback(self, **kwargs) -> tuple[bool, list[str]]:
        """
        Phase 1: strict day-spread cap (MAX_SLOTS_PER_CLASS_PER_DAY).
        Phase 2: if phase 1 fails, retry with cap raised to len(SLOTS)
                 (i.e. only the absolute hard limit: one entry per slot
                  per class per day).
        Emits a warning when the cap had to be relaxed.
        """
        placed, w = self._place(day_cap=MAX_SLOTS_PER_CLASS_PER_DAY, **kwargs)
        if placed:
            return True, w

        # Phase 2 — relax the day-spread soft cap
        placed, w2 = self._place(day_cap=len(SLOTS), **kwargs)
        if placed:
            entries = kwargs['entries']
            for entry in entries:
                w2.append(
                    f"{entry.Tclass.class_name} day-spread cap relaxed for "
                    f"{entry.course.course_code} — consider adding more venues "
                    f"or days to reduce congestion."
                )
        return placed, w + w2

    # ── core placement ────────────────────────────────────────────────

    def _place(
        self,
        entries,
        professors,
        venues,
        lecturer_busy,
        venue_busy,
        class_busy,
        class_day,
        slots,
        one_venue_each=False,
        start_idx=0,
        day_cap=MAX_SLOTS_PER_CLASS_PER_DAY,
        relax_lecturer=True,
    ) -> tuple[bool, list[str]]:
        """
        Try every (day, slot) combination starting from start_idx.
        Mutates busy dicts and appends to slots on success.
        Returns (placed, warnings).
        """
        warnings = []
        all_day_slots = [(d, s) for d in DAYS for s in SLOTS]
        n = len(all_day_slots)

        for offset in range(n):
            day, slot = all_day_slots[(start_idx + offset) % n]

            # hard: no class double-booking
            if any(class_busy.get((e.Tclass.pk, day, slot)) for e in entries):
                continue

            # soft cap on slots per day per class
            if any(class_day[(e.Tclass.pk, day)] >= day_cap for e in entries):
                continue

            # lecturer constraint (relaxable)
            lecturer_clash = bool(professors) and any(
                lecturer_busy.get((p.pk, day, slot)) for p in professors
            )
            if lecturer_clash and not relax_lecturer:
                continue

            # venue check
            if one_venue_each:
                assigned = self._free_venues(
                    venues, venue_busy, day, slot, len(entries))
            else:
                v = self._free_venue(venues, venue_busy, day, slot)
                assigned = [v] * len(entries) if v else None

            if not assigned:
                continue

            # ── commit ────────────────────────────────────────────────
            if lecturer_clash:
                for p in professors:
                    if lecturer_busy.get((p.pk, day, slot)):
                        warnings.append(
                            f"Lecturer {p.staff_number} double-booked on "
                            f"{day} {slot} (lecturer pool too small for load)."
                        )

            for professor in professors:
                lecturer_busy[(professor.pk, day, slot)] = True

            for entry, venue in zip(entries, assigned):
                venue_busy[(venue.pk, day, slot)] = True
                class_busy[(entry.Tclass.pk, day, slot)] = True
                class_day[(entry.Tclass.pk, day)] += 1

                cnt = class_day[(entry.Tclass.pk, day)]
                if cnt == MAX_SLOTS_PER_CLASS_PER_DAY:
                    warnings.append(
                        f"{entry.Tclass.class_name} now has {cnt} slots on "
                        f"{day} — consider distributing across the week."
                    )

                slots.append(TimetableSlot(
                    curriculum_id=str(entry.pk),
                    day=day,
                    time_slot=slot,
                    venue_id=str(venue.pk),
                    meta={
                        'course_code': entry.course.course_code,
                        'class_name':  entry.Tclass.class_name,
                    },
                ))

            return True, warnings

        return False, warnings

    # ── venue helpers ─────────────────────────────────────────────────

    def _free_venue(self, venues, venue_busy, day, slot):
        for v in venues:
            if not venue_busy.get((v.pk, day, slot)):
                return v
        return None

    def _free_venues(self, venues, venue_busy, day, slot, n):
        free = [v for v in venues if not venue_busy.get((v.pk, day, slot))]
        return free[:n] if len(free) >= n else None
