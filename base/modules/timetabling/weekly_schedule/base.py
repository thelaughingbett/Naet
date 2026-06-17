from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimetableSlot:
    """
    The normalised shape of one timetable entry.

    Every strategy returns a list of these.
    Naet maps them to Timetable model instances — the strategy
    never touches the DB directly.

    curriculum_id:  the Curriculum record this slot belongs to
    day:            must be one of Timetable.DAY_CHOICES keys
    time_slot:      must be one of Timetable.TIME_SLOTS keys e.g. '08:00-10:00'
    venue_id:       FK to Venue — strategy resolves this, Naet just stores it
    """
    curriculum_id: str          # UUID as string
    day:           str          # 'MON' | 'TUE' | 'WED' | 'THU' | 'FRI'
    time_slot:     str          # '08:00-10:00' | '10:00-12:00' | ...
    venue_id:      str          # UUID as string

    meta: Optional[dict] = None


@dataclass
class TimetableGenerationResult:
    """
    Returned by every strategy after attempting to generate a timetable.

    success:  False means nothing was written — caller should not proceed
    slots:    the proposed schedule — written to DB by Naet after validation
    message:  human-readable summary or error
    warnings: non-fatal issues the caller should know about
              e.g. ["CSC411 placed on Friday — lecturer requested Mon-Thu"]
    stats:    optional metadata from the strategy
              e.g. {"iterations": 142, "solver_status": "optimal"}
    """
    success:  bool
    slots:    list[TimetableSlot] = field(default_factory=list)
    message:  str = ""
    warnings: list[str] = field(default_factory=list)
    stats:    Optional[dict] = None


class AbstractTimetableStrategy(ABC):
    """
    Contract every timetable generation strategy must implement.

    Strategies are function-like objects — they receive a session,
    return a TimetableGenerationResult, and touch nothing in the DB.

    Everything else — clearing old slots, bulk-creating new ones,
    handling transactions — is done by the core after the strategy returns.

    ---

    How to register your strategy in settings.py:

        TIMETABLE_STRATEGY = 'base.modules.timetabling.strategies.greedy.GreedyStrategy'

    How the core loads it:

        from django.utils.module_loading import import_string
        strategy_class = import_string(settings.TIMETABLE_STRATEGY)
        strategy = strategy_class()
        result = strategy.generate(session)

    ---

    Implementors must follow these rules:

    1. NEVER write to the DB inside generate()
       Return slots — let Naet write them.

    2. ALWAYS catch your own exceptions
       Return TimetableGenerationResult(success=False, message=str(e))
       Never let an exception propagate out of generate().

    3. Validate your output before returning
       Use validate() — it checks day/time_slot values are legal
       before Naet tries to bulk_create and gets a DB error.

    4. Return warnings for soft constraint violations
       Don't raise for things like "lecturer prefers mornings" —
       add a warning string and still return success=True.
    """

    @abstractmethod
    def generate(self, session) -> TimetableGenerationResult:
        """
        Generate a complete timetable for the given session.

        Must place every Curriculum entry that belongs to the session.
        If any entry cannot be placed, return success=False — Naet
        will not write any slots to the DB in that case.

        session: a Session model instance (is_active=True, typically)
        """
        raise NotImplementedError

    def validate(self, result: TimetableGenerationResult) -> list[str]:
        """
        Validate the slots in a result before Naet writes them.

        Returns a list of error strings.
        Empty list = all good.

        Override to add strategy-specific validation on top of the
        base checks here.
        """
        from base.models import Timetable

        valid_days = {k for k, _ in Timetable.DAY_CHOICES}
        valid_slots = {k for k, _ in Timetable.TIME_SLOTS}

        errors = []

        for i, slot in enumerate(result.slots):
            if slot.day not in valid_days:
                errors.append(
                    f"Slot {i}: invalid day '{slot.day}' — "
                    f"must be one of {sorted(valid_days)}"
                )
            if slot.time_slot not in valid_slots:
                errors.append(
                    f"Slot {i}: invalid time_slot '{slot.time_slot}' — "
                    f"must be one of {sorted(valid_slots)}"
                )
            if not slot.curriculum_id:
                errors.append(f"Slot {i}: curriculum_id is empty")
            if not slot.venue_id:
                errors.append(f"Slot {i}: venue_id is empty")

        # check for internal double-bookings before hitting the DB
        venue_seen = {}
        class_seen = {}

        for i, slot in enumerate(result.slots):
            venue_key = (slot.venue_id, slot.day, slot.time_slot)
            if venue_key in venue_seen:
                errors.append(
                    f"Slot {i}: venue {slot.venue_id} double-booked "
                    f"at {slot.day} {slot.time_slot} "
                    f"(also slot {venue_seen[venue_key]})"
                )
            venue_seen[venue_key] = i

        return errors
