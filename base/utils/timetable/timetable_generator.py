# utils/timetable_generator.py

import pulp
from constraint import Problem, AllDifferentConstraint
from itertools import product

from base.models import Curriculum, Timetable, Venue
from django.db import transaction

from itertools import groupby
from base.models import Curriculum, Timetable, Venue
from django.db import transaction

DAYS = ('MON', 'TUE', 'WED', 'THU', 'FRI')

SLOTS = (
    '08:00-10:00',
    '10:00-12:00',
    '12:00-13:00',
    '13:00-15:00',
    '15:00-17:00',
    '17:00-19:00',
)


def generate_timetable(session):
    lecturer_busy = {}   # {(lecturer_id, day, slot): True}
    venue_busy = {}   # {(venue_id, day, slot): True}
    class_busy = {}   # {(tclass_id, day, slot): True}
    class_day = {}   # {(tclass_id, day): count}

    venues = list(Venue.objects.all())
    if not venues:
        raise Exception("No venues found. Add venues before generating.")

    curriculum = Curriculum.objects.filter(
        session=session
    ).select_related(
        'Tclass', 'course'
    ).prefetch_related('professor').order_by('course__course_type')

    to_create = []

    # split into common units and regular courses
    # {course_id: [entry, entry, ...]}  — CC grouped by course
    common_units = {}
    regular = []

    for entry in curriculum:
        if entry.course.course_type == 'CC':
            common_units.setdefault(entry.course_id, []).append(entry)
        else:
            regular.append(entry)

    # --- regular courses ---
    for entry in regular:
        professors = list(entry.professor.all())
        if not professors:
            raise Exception(
                f"{entry.course.course_code} ({entry.Tclass.class_name}) "
                f"has no assigned professor."
            )

        placed = _place_entry(
            entries=[entry],
            professors=professors,
            venues=venues,
            lecturer_busy=lecturer_busy,
            venue_busy=venue_busy,
            class_busy=class_busy,
            class_day=class_day,
            to_create=to_create,
            one_venue_each=False,   # all share one venue
        )

        if not placed:
            raise Exception(
                f"Could not place {entry.course.course_code} "
                f"for {entry.Tclass.class_name}."
            )

    # --- common units ---
    # all classes taking this CC go at the same slot
    # each class may have different professors
    for course_id, entries in common_units.items():
        # collect ALL professors across all classes for this common unit
        all_professors = []
        for entry in entries:
            all_professors.extend(list(entry.professor.all()))

        if not all_professors:
            course_code = entries[0].course.course_code
            raise Exception(
                f"Common unit {course_code} has no assigned professors "
                f"on any of its class entries."
            )

        placed = _place_entry(
            entries=entries,
            professors=all_professors,
            venues=venues,
            lecturer_busy=lecturer_busy,
            venue_busy=venue_busy,
            class_busy=class_busy,
            class_day=class_day,
            to_create=to_create,
            one_venue_each=True,    # each class gets its own venue
        )

        if not placed:
            course_code = entries[0].course.course_code
            raise Exception(
                f"Could not place common unit {course_code} — "
                f"no slot free for all {len(entries)} classes simultaneously."
            )

    with transaction.atomic():
        Timetable.objects.filter(curriculum__session=session).delete()
        created = Timetable.objects.bulk_create(to_create)

    return len(created)


def _place_entry(
    entries, professors, venues,
    lecturer_busy, venue_busy, class_busy, class_day,
    to_create, one_venue_each=False
):
    """
    Try to find a day+slot where:
    - All professors are free
    - All classes (entries) are free
    - Enough venues exist (one per entry if one_venue_each, else one shared)
    - No class exceeds 3 slots on the same day

    Returns True if placed, False if no slot found.
    """
    for day in DAYS:
        for slot in SLOTS:

            # check all professors free at this slot
            if any(lecturer_busy.get((p.pk, day, slot)) for p in professors):
                continue

            # check all classes free at this slot
            if any(class_busy.get((e.Tclass.pk, day, slot)) for e in entries):
                continue

            # check class day spread
            if any(class_day.get((e.Tclass.pk, day), 0) >= 3 for e in entries):
                continue

            # find venue(s)
            if one_venue_each:
                # each class needs its own venue
                assigned_venues = _find_n_free_venues(
                    venues, venue_busy, day, slot, n=len(entries)
                )
                if not assigned_venues:
                    continue
            else:
                # all classes share one venue
                venue = _find_free_venue(venues, venue_busy, day, slot)
                if not venue:
                    continue
                assigned_venues = [venue] * len(entries)

            # commit the booking
            for professor in professors:
                lecturer_busy[(professor.pk, day, slot)] = True

            for entry, venue in zip(entries, assigned_venues):
                venue_busy[(venue.pk, day, slot)] = True
                class_busy[(entry.Tclass.pk, day, slot)] = True
                class_day[(entry.Tclass.pk, day)] = (
                    class_day.get((entry.Tclass.pk, day), 0) + 1
                )
                to_create.append(
                    Timetable(
                        curriculum=entry,
                        day=day,
                        time_slot=slot,
                        venue=venue,
                    )
                )

            return True

    return False


def _find_free_venue(venues, venue_busy, day, slot):
    for venue in venues:
        if not venue_busy.get((venue.pk, day, slot)):
            return venue
    return None


def _find_n_free_venues(venues, venue_busy, day, slot, n):
    """Return n distinct free venues at this day/slot, or None if not enough."""
    free = [v for v in venues if not venue_busy.get((v.pk, day, slot))]
    return free[:n] if len(free) >= n else None


def generate_with_csp(session):
    problem = Problem()

    curriculum = Curriculum.objects.filter(
        session=session).select_related('Tclass', 'course')
    slots = [(day, time) for day in DAYS for time in SLOTS]

    # variable per curriculum entry
    for entry in curriculum:
        problem.addVariable(entry.pk, slots)

    # hard constraint — same class can't have two subjects in the same slot
    classes = {}
    for entry in curriculum:
        classes.setdefault(entry.Tclass.pk, []).append(entry.pk)

    for class_id, entries in classes.items():
        if len(entries) > 1:
            problem.addConstraint(AllDifferentConstraint(), entries)

    # hard constraint — same lecturer can't teach two things at once
    lecturers = {}
    for entry in curriculum:
        for prof in entry.professor.all():
            lecturers.setdefault(prof.pk, []).append(entry.pk)

    for lecturer_id, entries in lecturers.items():
        if len(entries) > 1:
            problem.addConstraint(AllDifferentConstraint(), entries)

    solution = problem.getSolution()
    if not solution:
        raise Exception('No valid timetable found for given constraints.')

    return solution  # {curriculum_pk: (day, slot)}


def generate_with_ilp(session):
    curriculum = list(Curriculum.objects.filter(session=session))
    slots = [(d, t) for d in DAYS for t in SLOTS]

    # binary decision variable: assign[entry][slot] = 1 if placed there
    assign = {
        (e.pk, s): pulp.LpVariable(f'x_{e.pk}_{s[0]}_{s[1]}', cat='Binary')
        for e in curriculum
        for s in slots
    }

    prob = pulp.LpProblem('timetable', pulp.LpMinimize)
    prob += 0  # no objective — just feasibility

    # each entry must be assigned exactly one slot
    for entry in curriculum:
        prob += pulp.lpSum(assign[(entry.pk, s)] for s in slots) == 1

    # no two entries in the same class at the same slot
    class_entries = {}
    for entry in curriculum:
        class_entries.setdefault(entry.Tclass.pk, []).append(entry)

    for class_id, entries in class_entries.items():
        for slot in slots:
            prob += pulp.lpSum(assign[(e.pk, slot)] for e in entries) <= 1

    # no two entries with the same lecturer at the same slot
    lecturer_entries = {}
    for entry in curriculum:
        for prof in entry.professor.all():
            lecturer_entries.setdefault(prof.pk, []).append(entry)

    for lecturer_id, entries in lecturer_entries.items():
        for slot in slots:
            prob += pulp.lpSum(assign[(e.pk, slot)] for e in entries) <= 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != 'Optimal':
        raise Exception('No feasible timetable found.')

    result = {}
    for entry in curriculum:
        for slot in slots:
            if pulp.value(assign[(entry.pk, slot)]) == 1:
                result[entry.pk] = slot

    return result
