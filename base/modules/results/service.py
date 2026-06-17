from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string

from base.models import Curriculum, Enrollment, Result, Session, Student


DEFAULT_STRATEGY = 'base.modules.results.strategies.excel.ExcelResultsStrategy'


def get_strategy():
    """Load the results strategy configured in settings."""
    path = getattr(settings, 'RESULTS_STRATEGY', DEFAULT_STRATEGY)
    try:
        strategy_class = import_string(path)
        return strategy_class()
    except ImportError as e:
        raise ImportError(
            f"Could not load results strategy '{path}'. "
            f"Check RESULTS_STRATEGY in settings.py. Error: {e}"
        )


def run_results_import(session, **kwargs) -> tuple[bool, str, int]:
    """
    Load the configured strategy, run it, validate the result,
    resolve FKs, and write to the DB.

    Returns (success, message, count_created).

    This is the only function that writes Result records via a strategy.
    Strategies never touch the DB — this function does.
    """
    strategy = get_strategy()
    result = strategy.load(session, **kwargs)

    if not result.success:
        return False, result.message, 0

    errors = strategy.validate(result)
    if errors:
        error_summary = (
            f"{len(errors)} validation error(s):\n"
            + "\n".join(f"  • {e}" for e in errors)
        )
        return False, error_summary, 0

    # resolve registration_number → Student
    # resolve course_code + session → Curriculum
    # only students with an approved enrollment can receive results
    student_map = {
        s.registration_number: s
        for s in Student.objects.filter(
            registration_number__in={
                e.registration_number for e in result.entries}
        )
    }

    curriculum_map = {
        c.course.course_code: c
        for c in Curriculum.objects.filter(session=session)
        .select_related('course')
    }

    approved_enrollments = set(
        Enrollment.objects.filter(
            curriculum__session=session,
            status='approved'
        ).values_list('student__registration_number', 'curriculum__course__course_code')
    )

    to_create = []
    warnings = list(result.warnings)

    for entry in result.entries:
        student = student_map.get(entry.registration_number)
        curriculum = curriculum_map.get(entry.course_code)

        if not student:
            warnings.append(
                f"{entry.registration_number}: student not found — skipped")
            continue

        if not curriculum:
            warnings.append(
                f"{entry.course_code}: course not in session curriculum — skipped")
            continue

        if (entry.registration_number, entry.course_code) not in approved_enrollments:
            warnings.append(
                f"{entry.registration_number} / {entry.course_code}: "
                f"no approved enrollment — skipped"
            )
            continue

        to_create.append(Result(
            student=student,
            curricula=curriculum,
            type=entry.result_type,
            score=entry.score,
            title=entry.title,
        ))

    if not to_create:
        return False, "No valid results to import after resolution.", 0

    with transaction.atomic():
        created = Result.objects.bulk_create(
            to_create,
            update_conflicts=True,
            unique_fields=['student', 'curricula', 'title'],
            update_fields=['score', 'type'],
        )

    warning_text = ""
    if warnings:
        warning_text = f" ({len(warnings)} warning(s))"

    return True, f"Imported {len(created)} results.{warning_text}", len(created)
