import datetime
import logging
from django.db import transaction
from django.utils.module_loading import import_string
from django.conf import settings
from django.db import models

from base.models import Curriculum, ExamSession, ExamVenue, Lecturer, Venue
from base.modules.timetabling.exam_timetable.base import (
    AbstractExamTimetableGenerator,
    ExamConstraints,
)
from base.modules.timetabling.exam_timetable.strategies.examples.greedy import GreedyExamGenerator

logger = logging.getLogger(__name__)

EXAM_SLOTS = (
    '08:00-11:00',
    '11:00-14:00',
    '14:00-17:00',
    '17:00-20:00',
)
EXAM_DAYS_BEFORE_END = 14


def _resolve_generator() -> AbstractExamTimetableGenerator:
    """Load the generator from settings, defaulting to greedy."""
    setting = getattr(settings, 'TIMETABLE_GENERATOR', None)

    if setting is None:
        return GreedyExamGenerator()

    if isinstance(setting, dict):
        cls = import_string(setting['backend'])
        return cls(**setting.get('options', {}))

    if isinstance(setting, str):
        cls = import_string(setting)
        return cls()

    if isinstance(setting, AbstractExamTimetableGenerator):
        return setting

    return GreedyExamGenerator()


def _build_constraints(session, exam_type) -> ExamConstraints:
    """Pre-fetch everything from the DB and pack into TimetableConstraints."""
    if not session.end_date:
        raise ValueError(
            "Session has no end date — set it before generating exams.")

    start = session.end_date - datetime.timedelta(days=EXAM_DAYS_BEFORE_END)
    exam_dates = [
        start + datetime.timedelta(days=i)
        for i in range(EXAM_DAYS_BEFORE_END + 1)
        if (start + datetime.timedelta(days=i)).weekday() < 5
    ]

    venues = list(Venue.objects.values('id', 'name', 'capacity'))
    invigilators = list(
        Lecturer.objects.select_related('user')
        .values('id', name=models.F('user__get_full_name'))
    )

    curriculum_qs = (
        Curriculum.objects
        .filter(session=session)
        .select_related('Tclass', 'course')
        .prefetch_related('professor', 'enrolled_students')
    )

    curriculum_entries = [
        {
            'id':                   entry.pk,
            'course_code':          entry.course.course_code,
            'class_name':           entry.Tclass.class_name,
            'enrolled_student_ids': list(
                entry.enrolled_students.values_list('record_id', flat=True)
            ),
            'professor_ids':        list(
                entry.professor.values_list('pk', flat=True)
            ),
        }
        for entry in curriculum_qs
    ]

    return ExamConstraints(
        session=session,
        exam_type=exam_type,
        exam_dates=exam_dates,
        slots=list(EXAM_SLOTS),
        curriculum_entries=curriculum_entries,
        venues=venues,
        invigilators=invigilators,
    )


def generate_exam_timetable(session, exam_type='MAIN') -> int:
    """
    Public entry point. Resolves the configured generator, builds constraints
    from the DB, runs the algorithm, then persists the result.

    Returns the number of ExamSession records created.
    Raises on hard failure or unplaced entries.
    """
    generator = _resolve_generator()
    logger.info(f"[timetable] Using generator: {generator.generator_name}")

    constraints = _build_constraints(session, exam_type)

    # pre-flight
    errors = generator.validate_constraints(constraints)
    if errors:
        raise ValueError(f"Timetable generation aborted: {'; '.join(errors)}")

    plan = generator.generate(constraints)

    # surface warnings
    for warning in plan.warnings:
        logger.warning(f"[timetable] {warning}")

    # treat unplaced entries as fatal
    if plan.warnings:
        raise Exception(
            f"Could not place {len(plan.warnings)} exam(s). "
            f"Add more dates or venues.\n" + "\n".join(plan.warnings)
        )

    # persist
    with transaction.atomic():
        ExamSession.objects.filter(
            curriculum__session=session,
            exam_type=exam_type,
        ).delete()

        created = ExamSession.objects.bulk_create([
            ExamSession(
                curriculum_id=s.curriculum_id,
                exam_type=s.exam_type,
                date=s.date,
                time_slot=s.time_slot,
            )
            for s in plan.slots
        ])

        ExamVenue.objects.bulk_create([
            ExamVenue(
                exam_session=exam_session,
                venue_id=s.venue_id,
                invigilator_id=s.invigilator_id,
            )
            for exam_session, s in zip(created, plan.slots)
        ])

    logger.info(
        f"[timetable] Generated {len(created)} exam sessions "
        f"via {generator.generator_name} for session {session}"
    )
    return len(created)
