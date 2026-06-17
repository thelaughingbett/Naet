# base/modules/exam_timetable/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class ExamSlot:
    """
    A single resolved exam placement.

    Returned inside an ExamPlan by every generator.
    The scheduler takes this list and bulk-creates ExamSession + ExamVenue records.
    Generators never write to the DB.

    curriculum_id:  PK of the Curriculum entry being examined
    date:           exam date
    time_slot:      must match ExamSession.TIME_SLOTS exactly e.g. '08:00-11:00'
    venue_id:       PK of the Venue to use
    invigilator_id: PK of the Lecturer acting as invigilator
    exam_type:      'MAIN' or 'SUPPLEMENTARY'
    metadata:       anything the generator wants to pass through for debugging
                    e.g. {'score': 0.97, 'iteration': 4} for ILP solvers
    """
    curriculum_id:  int | str
    date:           datetime.date
    time_slot:      str
    venue_id:       int | str
    invigilator_id: int | str
    exam_type:      str = 'MAIN'
    metadata:       dict = field(default_factory=dict)


@dataclass
class ExamPlan:
    """
    The complete output of one generator run.

    Returned by AbstractExamTimetableGenerator.generate().
    The scheduler validates and persists this — the generator never does.

    slots:    the full list of resolved placements — one per curriculum entry
    warnings: non-fatal issues the generator noticed e.g. 'preferred invigilator
              unavailable for CS101 — assigned fallback'
    metadata: summary stats for logging e.g. {'solver': 'CBC', 'gap': 0.001}
    """
    slots:    list[ExamSlot] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ExamConstraints:
    """
    All the raw data a generator needs to do its work.

    Built by the scheduler from the DB and passed into generate().
    Generators never query the DB themselves.

    session:             the Session being scheduled
    exam_type:           'MAIN' or 'SUPPLEMENTARY'
    exam_dates:          ordered list of candidate weekday dates
    slots:               time slot strings in order e.g. ['08:00-11:00', ...]
    curriculum_entries:  list of dicts — one per Curriculum row, pre-fetched:
                         {
                           'id':                   curriculum PK,
                           'course_code':           str,
                           'class_name':            str,
                           'enrolled_student_ids':  [pk, ...],
                           'professor_ids':         [pk, ...],
                         }
    venues:              [{'id': pk, 'name': str, 'capacity': int}, ...]
    invigilators:        [{'id': pk, 'name': str}, ...]
    """
    session:            object
    exam_type:          str
    exam_dates:         list[datetime.date]
    slots:              list[str]
    curriculum_entries: list[dict]
    venues:             list[dict]
    invigilators:       list[dict]


class AbstractExamTimetableGenerator(ABC):
    """
    Contract every exam timetable generation algorithm must implement.

    The generator receives a fully-populated ExamConstraints object
    and returns an ExamPlan. It never touches the database.
    Persistence, validation, and conflict-checking after generation are
    handled by the scheduler service in scheduler.py.

    ---

    Built-in implementations:

        GreedyExamGenerator    →  generators/greedy.py
            The default. Fast, deterministic, slot-by-slot placement.
            Good for small-to-medium cohorts.

        ILPExamGenerator       →  generators/ilp.py
            Integer Linear Programming via PuLP or OR-Tools.
            Globally optimal — minimises student clashes across all units.
            Slower; requires a solver installed (CBC bundled with PuLP).

        ExcelImportGenerator   →  generators/excel.py
            Reads a pre-filled Excel timetable and converts it into an
            ExamPlan. For institutions that schedule manually first.

    ---

    Configuration (settings.py):

        EXAM_TIMETABLE_GENERATOR = 'base.modules.exam_timetable.generators.greedy.GreedyExamGenerator'
        EXAM_TIMETABLE_GENERATOR = 'base.modules.exam_timetable.generators.ilp.ILPExamGenerator'
        EXAM_TIMETABLE_GENERATOR = {
            'backend': 'base.modules.exam_timetable.generators.ilp.ILPExamGenerator',
            'options': {
                'solver':     'CBC',
                'time_limit': 120,
                'gap':        0.01,
            }
        }

    ---

    Execution contract:

        1. NEVER query the database inside generate().
           All data arrives via ExamConstraints.

        2. NEVER write to the database inside generate().
           Return an ExamPlan. The scheduler does the bulk_create.

        3. NEVER raise for soft failures.
           Unplaceable entries → add to ExamPlan.warnings and skip.
           Raise only for hard failures (solver crash, malformed input).

        4. Every curriculum entry must appear exactly once in ExamPlan.slots
           unless it was skipped with a warning.

        5. time_slot values must exactly match ExamSession.TIME_SLOTS choices.

        6. venue_id and invigilator_id must be PKs from the lists in
           ExamConstraints.

    ---

    Writing a custom generator:

        from base.modules.exam_timetable.base import (
            AbstractExamTimetableGenerator,
            ExamConstraints,
            ExamPlan,
            ExamSlot,
        )

        class MyExamGenerator(AbstractExamTimetableGenerator):
            generator_name = 'my_custom'

            def generate(self, constraints: ExamConstraints) -> ExamPlan:
                plan = ExamPlan()
                for entry in constraints.curriculum_entries:
                    plan.slots.append(ExamSlot(
                        curriculum_id=  entry['id'],
                        date=           constraints.exam_dates[0],
                        time_slot=      constraints.slots[0],
                        venue_id=       constraints.venues[0]['id'],
                        invigilator_id= constraints.invigilators[0]['id'],
                        exam_type=      constraints.exam_type,
                    ))
                return plan

        Register in settings.py:
            EXAM_TIMETABLE_GENERATOR = 'myapp.generators.MyExamGenerator'
    """

    generator_name: str = ""

    @abstractmethod
    def generate(self, constraints: ExamConstraints) -> ExamPlan:
        """
        Generate a full exam timetable from the given constraints.

        constraints:  pre-fetched data — dates, venues, curriculum, students
        returns:      ExamPlan with one ExamSlot per placed entry
        raises:       only on hard failure (solver crash, malformed input)
        """
        raise NotImplementedError

    def describe(self) -> str:
        return self.__class__.__name__

    def validate_constraints(self, constraints: ExamConstraints) -> list[str]:
        """
        Optional pre-flight check before generate() is called.
        Return a list of error strings — empty list means all clear.
        The scheduler calls this first and aborts if errors are returned.
        Override to add algorithm-specific requirement checks.
        """
        errors = []
        if not constraints.exam_dates:
            errors.append("No exam dates provided.")
        if not constraints.venues:
            errors.append("No venues available.")
        if not constraints.invigilators:
            errors.append("No invigilators available.")
        if not constraints.curriculum_entries:
            errors.append("No curriculum entries to schedule.")
        return errors
