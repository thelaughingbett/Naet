"""
Timetabling Module

Schedules two distinct things, each through its own pluggable generator:

    weekly_schedule  →  which class takes which course, when, and where
    exam_timetable   →  which course is examined, when, where, and who invigilates

Both follow the same shape: a generator receives everything it needs as
plain data, proposes a schedule, and never touches the database itself.
A single core file per submodule — weekly_schedule/service.py and
exam_timetable/scheduler.py — is the only place allowed to write the
result. The default algorithm for both is a greedy, slot-by-slot solver;
an institution that needs something smarter (an ILP solver, a manual
Excel import) can swap it in via settings without changing anything else.


Folder Structure Reference:
    base/modules/timetabling/
    ├── __init__.py            # this file
    ├── weekly_schedule/
    │   ├── base.py              # AbstractTimetableStrategy, TimetableSlot, TimetableGenerationResult
    │   ├── service.py             # run_timetable_generation() — writes Timetable rows
    │   └── strategies/
    │       ├── contrib/             # community-contributed strategies
    │       └── examples/
    │           ├── greedy.py          # GreedyStrategy — the default
    │           ├── ilp.py               # ILPStrategy — globally optimal via PuLP / OR-Tools
    │           └── excel.py               # ExcelImportStrategy — read a pre-filled timetable
    └── exam_timetable/
        ├── base.py              # AbstractExamTimetableGenerator, ExamConstraints, ExamPlan, ExamSlot
        ├── scheduler.py           # generate_exam_timetable() — writes ExamSession + ExamVenue rows
        └── strategies/
            ├── contrib/             # community-contributed generators
            └── examples/
                ├── greedy.py          # GreedyExamGenerator — the default
                ├── ilp.py               # for institutions wanting a globally-optimal solve
                └── excel.py               # read a pre-filled exam timetable


Configuration (settings.py):

    The two submodules are configured independently, since each needs a
    different shape of input.

    Weekly schedule reads a single dict:

        TIMETABLE_MODULE_CONFIG = {
            "STRATEGY": "base.modules.timetabling.weekly_schedule.strategies.examples.greedy.GreedyStrategy",
            "DAYS":  [("MON", "Monday"), ("TUE", "Tuesday"), ...],
            "SLOTS": [("08:00-10:00", "8 – 10am"), ...],
        }

    Exam timetable reads a single setting, in one of three forms:

        # dotted import path
        TIMETABLE_GENERATOR = "base.modules.timetabling.exam_timetable.strategies.examples.greedy.GreedyExamGenerator"

        # dict — backend + constructor options
        TIMETABLE_GENERATOR = {
            "backend": "base.modules.timetabling.exam_timetable.strategies.examples.ilp.ILPExamGenerator",
            "options": {"solver": "CBC", "time_limit": 120, "gap": 0.01},
        }

        # an already-instantiated generator (handy in tests)
        TIMETABLE_GENERATOR = MyExamGenerator()


Usage:

    from base.modules.timetabling import run_timetable_generation, generate_exam_timetable

    success, message, count = run_timetable_generation(session)
    count = generate_exam_timetable(session, exam_type='MAIN')


Writing a Custom Weekly Strategy:

    Subclass AbstractTimetableStrategy and implement generate():

        from base.modules.timetabling.weekly_schedule.base import (
            AbstractTimetableStrategy,
            TimetableGenerationResult,
            TimetableSlot,
        )

        class MyStrategy(AbstractTimetableStrategy):
            def generate(self, session) -> TimetableGenerationResult:
                try:
                    slots = [...]   # build TimetableSlot objects
                    return TimetableGenerationResult(success=True, slots=slots)
                except Exception as e:
                    return TimetableGenerationResult(success=False, message=str(e))

    Place institution-specific strategies directly in strategies/,
    reference implementations in strategies/examples/, and community
    contributions in strategies/contrib/.


Writing a Custom Exam Generator:

    Subclass AbstractExamTimetableGenerator and implement generate():

        from base.modules.timetabling.exam_timetable.base import (
            AbstractExamTimetableGenerator,
            ExamConstraints,
            ExamPlan,
            ExamSlot,
        )

        class MyExamGenerator(AbstractExamTimetableGenerator):
            generator_name = "my_custom"

            def generate(self, constraints: ExamConstraints) -> ExamPlan:
                plan = ExamPlan(metadata={"generator": self.generator_name})
                for entry in constraints.curriculum_entries:
                    plan.slots.append(ExamSlot(
                        curriculum_id=entry["id"],
                        date=constraints.exam_dates[0],
                        time_slot=constraints.slots[0],
                        venue_id=constraints.venues[0]["id"],
                        invigilator_id=constraints.invigilators[0]["id"],
                        exam_type=constraints.exam_type,
                    ))
                return plan

    Same placement convention as weekly strategies: strategies/ for your
    own implementation, strategies/examples/ for a reference others can
    learn from, strategies/contrib/ for community contributions.


Execution Contract:

    - Generators never query or write to the database. All input arrives
      as plain data (a Session, or a pre-built ExamConstraints); all
      output is a plain result object (TimetableGenerationResult or
      ExamPlan) that the core service/scheduler validates and persists.

    - generate() must never raise for an ordinary scheduling outcome.
      Catch your own exceptions and report failure through the result
      object. Reserve real exceptions for genuinely unexpected failures
      — a malformed input, a solver crash.

    - Hard constraints fail the run; soft constraints are warnings.
      In the weekly strategy, a warning can still accompany a successful
      write. In the exam scheduler, any warning currently blocks the
      write entirely — design a custom exam generator's warnings with
      that in mind.

    - Regeneration is destructive by design. Both core files clear
      existing records for the session before writing new ones, inside
      a single atomic transaction.

    - Validate before persisting. Both submodules run a validation pass
      — legal day/slot values, no internal double-bookings — before the
      result ever reaches the database.
"""

from base.modules.timetabling.weekly_schedule.service import run_timetable_generation
from base.modules.timetabling.exam_timetable.scheduler import generate_exam_timetable

__all__ = [
    'run_timetable_generation',
    'generate_exam_timetable',
]
