"""
GreedyStrategy — bulk-tolerant timetable generator.

Key behaviours vs a naive greedy:
  - Round-robin slot selection spreads entries evenly across the week.
  - Two-phase placement: tries strict day-spread cap first, then
    relaxes it automatically per-entry if needed rather than failing.
  - Curricula with the most attending classes are placed first so they
    get first pick of slots.
  - Lecturer over-subscription is a warning not a failure (necessary
    when the lecturer pool is small relative to class count).
  - Missing professors produce a warning and placement continues.
  - validate() is still called before returning success.

SCHEMA NOTE: Curriculum is keyed by (course, session) and shared across
every class attending it (via the `classes` M2M / CurriculumClass
through-table) — it no longer has a direct `Tclass` field, and there is
no more "regular, single-class" case as distinct from "common unit":
EVERY Curriculum entry is placed once and simultaneously blocks the
slot for every class in `entry.classes.all()`. The old regular/CC split
and the old per-class `entry.Tclass` references have been removed
accordingly — CC courses are no longer structurally special, though
`course_type` is still available if you want to weight them differently
in sorting.

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
            .select_related('course')
            .prefetch_related('professor', 'classes')
        )

        if not curriculum_qs.exists():
            return TimetableGenerationResult(
                success=False,
                message=f"No curriculum entries found for {session}.",
            )

        all_entries = list(curriculum_qs)

        # Drop any entry with no attending classes at all — nothing to
        # place, and it would otherwise pass every check trivially and
        # burn a slot for no one.
        entries_with_classes = []
        skipped = []
        for entry in all_entries:
            classes = list(entry.classes.all())
            if not classes:
                skipped.append(entry.course.course_code)
                continue
            entries_with_classes.append((entry, classes))

        if not entries_with_classes:
            return TimetableGenerationResult(
                success=False,
                message=f"No curriculum entries with attending classes for {session}.",
            )

        # Busiest curricula (most attending classes, i.e. widest shared
        # lecture) placed first — they're the hardest to fit since they
        # block the most class-slots at once, so give them first pick.
        entries_with_classes.sort(key=lambda pair: -len(pair[1]))

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

        if skipped:
            warnings.append(
                f"Skipped {len(skipped)} curriculum entr{'y' if len(skipped) == 1 else 'ies'} "
                f"with no attending classes: {', '.join(skipped)}."
            )

        # ── place every curriculum entry (simultaneously across all its
        #    attending classes) ─────────────────────────────────────────
        for entry, classes in entries_with_classes:
            professors = list(entry.professor.all())

            if not professors:
                class_names = ', '.join(c.class_name for c in classes)
                warnings.append(
                    f"{entry.course.course_code} ({class_names}) "
                    f"has no assigned professor — placed without lecturer constraint."
                )

            start = advance_cursor()
            placed, w = self._place_with_fallback(
                entry=entry,
                classes=classes,
                professors=professors,
                venues=venues,
                lecturer_busy=lecturer_busy,
                venue_busy=venue_busy,
                class_busy=class_busy,
                class_day=class_day,
                slots=slots,
                start_idx=start,
            )
            warnings.extend(w)

            if not placed:
                class_names = ', '.join(c.class_name for c in classes)
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Could not place {entry.course.course_code} "
                        f"for [{class_names}] — all "
                        f"{len(all_day_slots)} day/slot combinations "
                        f"exhausted even after relaxing day-spread limit."
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
                'total_slots': len(slots),
                'curricula':   len(entries_with_classes),
                'warnings':    len(warnings),
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
            entry = kwargs['entry']
            classes = kwargs['classes']
            class_names = ', '.join(c.class_name for c in classes)
            w2.append(
                f"[{class_names}] day-spread cap relaxed for "
                f"{entry.course.course_code} — consider adding more venues "
                f"or days to reduce congestion."
            )
        return placed, w + w2

    # ── core placement ────────────────────────────────────────────────

    def _place(
        self,
        entry,
        classes,
        professors,
        venues,
        lecturer_busy,
        venue_busy,
        class_busy,
        class_day,
        slots,
        start_idx=0,
        day_cap=MAX_SLOTS_PER_CLASS_PER_DAY,
        relax_lecturer=True,
    ) -> tuple[bool, list[str]]:
        """
        Try every (day, slot) combination starting from start_idx for a
        single shared curriculum entry, checking/blocking it against
        every class in `classes` simultaneously (it's one physical
        lecture attended by all of them at once). Mutates busy dicts and
        appends one TimetableSlot to `slots` on success.
        Returns (placed, warnings).
        """
        warnings = []
        all_day_slots = [(d, s) for d in DAYS for s in SLOTS]
        n = len(all_day_slots)

        for offset in range(n):
            day, slot = all_day_slots[(start_idx + offset) % n]

            # hard: no class double-booking, for ANY attending class
            if any(class_busy.get((c.pk, day, slot)) for c in classes):
                continue

            # soft cap on slots per day, for ANY attending class
            if any(class_day[(c.pk, day)] >= day_cap for c in classes):
                continue

            # lecturer constraint (relaxable)
            lecturer_clash = bool(professors) and any(
                lecturer_busy.get((p.pk, day, slot)) for p in professors
            )
            if lecturer_clash and not relax_lecturer:
                continue

            # venue check — one shared venue for the whole lecture
            venue = self._free_venue(venues, venue_busy, day, slot)
            if venue is None:
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

            venue_busy[(venue.pk, day, slot)] = True

            for c in classes:
                class_busy[(c.pk, day, slot)] = True
                class_day[(c.pk, day)] += 1

                cnt = class_day[(c.pk, day)]
                if cnt == MAX_SLOTS_PER_CLASS_PER_DAY:
                    warnings.append(
                        f"{c.class_name} now has {cnt} slots on "
                        f"{day} — consider distributing across the week."
                    )

            slots.append(TimetableSlot(
                curriculum_id=str(entry.pk),
                day=day,
                time_slot=slot,
                venue_id=str(venue.pk),
                meta={
                    'course_code': entry.course.course_code,
                    'class_names': [c.class_name for c in classes],
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
