from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string

from base.models import Timetable


DEFAULT_STRATEGY = 'base.modules.timetabling.strategies.greedy.GreedyStrategy'


def get_strategy():
    """Load the strategy class configured in settings."""
    path = getattr(settings, 'TIMETABLE_MODULE_CONFIG', {}).get(
        'STRATEGY', DEFAULT_STRATEGY
    )
    try:
        strategy_class = import_string(path)
        return strategy_class()
    except ImportError as e:
        raise ImportError(
            f"Could not load timetable strategy '{path}'. "
            f"Check TIMETABLE_STRATEGY in settings.py. Error: {e}"
        )


def run_timetable_generation(session) -> tuple[bool, str, int]:
    """
    Load the configured strategy, run it, validate the result,
    and write to the DB if everything is clean.

    Returns (success, message, count_created).

    This is the only function that writes Timetable records.
    Strategies never touch the DB — this function does.
    """
    strategy = get_strategy()

    # run the strategy
    result = strategy.generate(session)

    if not result.success:
        return False, result.message, 0

    # validate before touching the DB
    errors = strategy.validate(result)
    if errors:
        error_summary = f"{len(errors)} validation error(s):\n" + \
            "\n".join(f"  • {e}" for e in errors)
        return False, error_summary, 0

    # write atomically — all or nothing
    with transaction.atomic():
        Timetable.objects.filter(curriculum__session=session).delete()

        created = Timetable.objects.bulk_create([
            Timetable(
                curriculum_id=slot.curriculum_id,
                day=slot.day,
                time_slot=slot.time_slot,
                venue_id=slot.venue_id,
            )
            for slot in result.slots
        ])

    # surface warnings after successful write
    warning_text = ""
    if result.warnings:
        warning_text = f" ({len(result.warnings)} warning(s): {'; '.join(result.warnings[:3])})"

    return True, f"Generated {len(created)} slots.{warning_text}", len(created)
