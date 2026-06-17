from base.modules.timetabling.weekly_schedule.base import (
    AbstractTimetableStrategy,
    TimetableSlot,
    TimetableGenerationResult,
)

from django.conf import settings

# 1. Fetch the config dictionary safely
config = getattr(settings, 'TIMETABLE_MODULE_CONFIG', {})

# 2. Extract only the first element (the key/code) from each tuple pair
DAYS = tuple(day[0] for day in config.get('DAYS', ()))
SLOTS = tuple(slot[0] for slot in config.get('SLOTS', ()))

MAX_SLOTS_PER_CLASS_PER_DAY = 3


class GreedyStrategy(AbstractTimetableStrategy):
    """
    Greedy timetable generator with backtracking.

    Places each curriculum entry by trying every (day, slot, venue)
    combination in order until one works. Common units (CC) are
    scheduled together — all classes sharing the course go at the
    same time, each getting their own venue.

    Register in settings.py:
        TIMETABLE_STRATEGY = 'base.modules.timetabling.strategies.greedy.GreedyStrategy'

    Soft constraints (produce warnings, not failures):
        - More than 2 slots on the same day for one class
        - All slots for a class fall on the same day

    Hard constraints (failure if violated):
        - Lecturer double-booked at same day/slot
        - Class double-booked at same day/slot
        - No free venue at the required day/slot
        - A common unit cannot be placed at any slot simultaneously

    Raises nothing — all errors returned via TimetableGenerationResult.
    """

    def generate(self, session) -> TimetableGenerationResult:
        try:
            return self._generate(session)
        except Exception as e:
            return TimetableGenerationResult(
                success=False,
                message=f"Unexpected error during generation: {e}"
            )

    def _generate(self, session) -> TimetableGenerationResult:
        from base.models import Curriculum, Venue

        venues = list(Venue.objects.all())
        if not venues:
            return TimetableGenerationResult(
                success=False,
                message="No venues found. Add venues before generating a timetable."
            )

        curriculum = (
            Curriculum.objects
            .filter(session=session)
            .select_related('Tclass', 'course')
            .prefetch_related('professor')
            # process CC last — they need simultaneous slots
            .order_by('course__type')
        )

        if not curriculum.exists():
            return TimetableGenerationResult(
                success=False,
                message=f"No curriculum entries found for {session}."
            )

        # ── booking state (in-memory only) ────────────────────────────
        lecturer_busy = {}  # {(lecturer_id, day, slot): True}
        venue_busy = {}  # {(venue_id, day, slot): True}
        class_busy = {}  # {(tclass_id, day, slot): True}
        class_day = {}  # {(tclass_id, day): count}

        slots = []     # [TimetableSlot, ...]
        warnings = []

        # ── split CC from regular ─────────────────────────────────────
        common_units = {}  # {course_id: [entry, ...]}
        regular = []

        for entry in curriculum:
            if entry.course.type == 'CC':
                common_units.setdefault(entry.course_id, []).append(entry)
            else:
                regular.append(entry)

        # ── place regular courses ─────────────────────────────────────
        for entry in regular:
            professors = list(entry.professor.all())
            if not professors:
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"{entry.course.course_code} "
                        f"({entry.Tclass.class_name}) has no assigned professor. "
                        f"Assign professors before generating."
                    )
                )

            placed, entry_warnings = self._place(
                entries=[entry],
                professors=professors,
                venues=venues,
                lecturer_busy=lecturer_busy,
                venue_busy=venue_busy,
                class_busy=class_busy,
                class_day=class_day,
                slots=slots,
                one_venue_each=False,
            )

            warnings.extend(entry_warnings)

            if not placed:
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Could not place {entry.course.course_code} "
                        f"for {entry.Tclass.class_name} — "
                        f"no available slot found."
                    )
                )

        # ── place common units ────────────────────────────────────────
        for course_id, entries in common_units.items():
            all_professors = []
            for entry in entries:
                all_professors.extend(list(entry.professor.all()))

            if not all_professors:
                course_code = entries[0].course.course_code
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Common unit {course_code} has no assigned professors "
                        f"on any of its class entries."
                    )
                )

            placed, entry_warnings = self._place(
                entries=entries,
                professors=all_professors,
                venues=venues,
                lecturer_busy=lecturer_busy,
                venue_busy=venue_busy,
                class_busy=class_busy,
                class_day=class_day,
                slots=slots,
                one_venue_each=True,  # each class needs its own venue
            )

            warnings.extend(entry_warnings)

            if not placed:
                course_code = entries[0].course.course_code
                return TimetableGenerationResult(
                    success=False,
                    message=(
                        f"Could not place common unit {course_code} — "
                        f"no slot free for all {len(entries)} classes simultaneously."
                    )
                )

        # ── validate before returning ─────────────────────────────────
        result = TimetableGenerationResult(
            success=True,
            slots=slots,
            warnings=warnings,
            message=f"Generated {len(slots)} slots.",
            stats={
                'total_slots':  len(slots),
                'common_units': len(common_units),
                'regular':      len(regular),
            }
        )

        errors = self.validate(result)
        if errors:
            return TimetableGenerationResult(
                success=False,
                message=f"Validation failed with {len(errors)} error(s): {errors[0]}",
                warnings=warnings,
            )

        return result

    # ── placement helper ──────────────────────────────────────────────

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
    ) -> tuple[bool, list[str]]:
        """
        Try every (day, slot) combination until a valid one is found.
        Returns (placed: bool, warnings: list[str]).

        No DB access — mutates the busy dicts and appends to slots.
        """
        warnings = []

        for day in DAYS:
            for slot in SLOTS:

                # hard: all professors free
                if any(lecturer_busy.get((p.pk, day, slot)) for p in professors):
                    continue

                # hard: all classes free
                if any(class_busy.get((e.Tclass.pk, day, slot)) for e in entries):
                    continue

                # hard: class day spread limit
                if any(
                    class_day.get((e.Tclass.pk, day),
                                  0) >= MAX_SLOTS_PER_CLASS_PER_DAY
                    for e in entries
                ):
                    continue

                # find venue(s)
                if one_venue_each:
                    assigned = self._free_venues(
                        venues, venue_busy, day, slot, n=len(entries))
                else:
                    v = self._free_venue(venues, venue_busy, day, slot)
                    assigned = [v] * len(entries) if v else None

                if not assigned:
                    continue

                # ── commit ────────────────────────────────────────────
                for professor in professors:
                    lecturer_busy[(professor.pk, day, slot)] = True

                for entry, venue in zip(entries, assigned):
                    venue_busy[(venue.pk, day, slot)] = True
                    class_busy[(entry.Tclass.pk, day, slot)] = True

                    day_count = class_day.get((entry.Tclass.pk, day), 0) + 1
                    class_day[(entry.Tclass.pk, day)] = day_count

                    # soft: warn if class is getting heavy on this day
                    if day_count == MAX_SLOTS_PER_CLASS_PER_DAY:
                        warnings.append(
                            f"{entry.Tclass.class_name} now has "
                            f"{day_count} slots on {day} — "
                            f"consider distributing across the week."
                        )

                    slots.append(TimetableSlot(
                        curriculum_id=str(entry.pk),
                        day=day,
                        time_slot=slot,
                        venue_id=str(venue.pk),
                        meta={
                            'course_code': entry.course.course_code,
                            'class_name':  entry.Tclass.class_name,
                        }
                    ))

                return True, warnings

        return False, warnings

    # ── venue helpers ─────────────────────────────────────────────────

    def _free_venue(self, venues, venue_busy, day, slot):
        for venue in venues:
            if not venue_busy.get((venue.pk, day, slot)):
                return venue
        return None

    def _free_venues(self, venues, venue_busy, day, slot, n):
        """Return n distinct free venues at this day/slot, or None."""
        free = [v for v in venues if not venue_busy.get((v.pk, day, slot))]
        return free[:n] if len(free) >= n else None
