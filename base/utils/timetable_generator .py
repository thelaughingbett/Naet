# utils/timetable_generator.py

import pulp
from constraint import Problem, AllDifferentConstraint
from itertools import product
from base.models import Timetable, Tclass, Curriculum, Session

DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI']
SLOTS = ['08:00', '09:00', '10:00', '11:00',
         '13:00', '14:00', '15:00', '16:00']


def generate_timetable(session):
    """
    Greedy timetable generator with backtracking.
    Returns list of Timetable dicts or raises if unsolvable.
    """

    # track what's booked
    lecturer_busy = {}   # {(lecturer_id, day, slot): True}
    venue_busy = {}   # {(venue, day, slot): True}
    class_busy = {}   # {(class_id, day, slot): True}
    class_day = {}   # {(class_id, day): count} — spread check

    curriculum = Curriculum.objects.filter(
        session=session
    ).select_related(
        'Tclass', 'course'
    ).prefetch_related('professor')

    result = []

    for entry in curriculum:
        placed = False

        for day in DAYS:
            for slot in SLOTS:
                professors = list(entry.professor.all())
                if not professors:
                    continue

                professor = professors[0]  # primary professor

                # check all hard constraints
                if lecturer_busy.get((professor.pk, day, slot)):
                    continue
                if class_busy.get((entry.Tclass.pk, day, slot)):
                    continue

                # find a free venue
                venue = _find_free_venue(venue_busy, day, slot)
                if not venue:
                    continue

                # soft: don't put more than 3 slots on same day for one class
                if class_day.get((entry.Tclass.pk, day), 0) >= 3:
                    continue

                # place it
                lecturer_busy[(professor.pk, day, slot)] = True
                venue_busy[(venue, day, slot)] = True
                class_busy[(entry.Tclass.pk, day, slot)] = True
                class_day[(entry.Tclass.pk, day)] = class_day.get(
                    (entry.Tclass.pk, day), 0
                ) + 1

                result.append({
                    'session':    session,
                    'tclass':     entry.Tclass,
                    'course':     entry.course,
                    'lecturer':   professor,
                    'day':        day,
                    'start_time': slot,
                    'end_time':   _next_slot(slot),
                    'venue':      venue,
                })
                placed = True
                break

            if placed:
                break

        if not placed:
            raise Exception(
                f'Could not place {entry.course.course_code} '
                f'for {entry.Tclass.class_name} — '
                f'no available slot found.'
            )

    return result


def _find_free_venue(venue_busy, day, slot):
    venues = ['Hall A', 'Hall B', 'Hall C',
              'Lab 1', 'Lab 2', 'Room 101', 'Room 102']
    for venue in venues:
        if not venue_busy.get((venue, day, slot)):
            return venue
    return None


def _next_slot(slot):
    slots = ['08:00', '09:00', '10:00', '11:00',
             '13:00', '14:00', '15:00', '16:00']
    i = slots.index(slot)
    return slots[i + 1] if i + 1 < len(slots) else '17:00'


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
