from django.db import transaction
from base.models import (
    Curriculum, ExamSession, ExamVenue, Lecturer, Session, Student, Venue
)

# must match ExamSession.TIME_SLOTS values exactly
EXAM_SLOTS = (
    '08:00-11:00',
    '11:00-14:00',
    '14:00-17:00',
    '17:00-20:00',
)

# how many exam days to spread across
# generator will pick dates from session end window
EXAM_DAYS_BEFORE_END = 14  # start exams 14 days before session end


def generate_exam_timetable(session, exam_type='MAIN'):
    """
    Greedy exam timetable generator.

    Constraints:
      - A class can't have two exams at the same date+slot
      - A venue can't host two exams at the same date+slot
      - An invigilator can't be in two venues at the same date+slot
      - A student can't have two exams at the same date+slot (clash detection)
      - Max 4 exams per day across all classes (slot limit)

    Returns count of ExamSession records created.
    Raises if any curriculum entry can't be placed.
    """

    import datetime

    if not session.end_date:
        raise Exception(
            "Session has no end date — set it before generating exams.")

    # build exam date window: N days before session end, weekdays only
    exam_dates = _get_exam_dates(session.end_date, EXAM_DAYS_BEFORE_END)
    if not exam_dates:
        raise Exception("No valid exam dates found in the session window.")

    venues = list(Venue.objects.all())
    invigilators = list(Lecturer.objects.select_related('user').all())

    if not venues:
        raise Exception("No venues found. Add venues before generating.")
    if not invigilators:
        raise Exception("No lecturers found to act as invigilators.")

    # busy trackers
    venue_busy = {}   # {(venue_id, date, slot): True}
    invig_busy = {}   # {(lecturer_id, date, slot): True}
    class_busy = {}   # {(tclass_id, date, slot): True}
    student_busy = {}   # {(student_id, date, slot): True} — clash prevention

    curriculum = Curriculum.objects.filter(
        session=session
    ).select_related(
        'Tclass', 'course'
    ).prefetch_related(
        'professor',
        'enrolled_students',  # through Enrollment
    ).order_by('course__course_type', 'Tclass')

    exam_sessions_to_create = []
    exam_venues_to_create = []

    # track which ExamSession maps to which curriculum
    # so we can attach ExamVenue after bulk_create
    # [(curriculum_entry, date, slot, venue, invigilator), ...]
    placement_map = []

    for entry in curriculum:
        placed = False

        # get all students enrolled in this curriculum
        enrolled_student_ids = list(
            entry.enrolled_students.values_list('record_id', flat=True)
        )

        for date in exam_dates:
            if placed:
                break

            for slot in EXAM_SLOTS:
                # class already has an exam at this date+slot
                if class_busy.get((entry.Tclass.pk, date, slot)):
                    continue

                # check no student clash
                clash = any(
                    student_busy.get((sid, date, slot))
                    for sid in enrolled_student_ids
                )
                if clash:
                    continue

                # find a free venue
                venue = _find_free_venue(venues, venue_busy, date, slot)
                if not venue:
                    continue

                # find a free invigilator
                # prefer the course's own professor, fall back to any free lecturer
                invigilator = _find_invigilator(
                    preferred=list(entry.professor.all()),
                    all_lecturers=invigilators,
                    invig_busy=invig_busy,
                    date=date,
                    slot=slot,
                )
                if not invigilator:
                    continue

                # commit
                class_busy[(entry.Tclass.pk, date, slot)] = True
                venue_busy[(venue.pk, date, slot)] = True
                invig_busy[(invigilator.pk, date, slot)] = True

                for sid in enrolled_student_ids:
                    student_busy[(sid, date, slot)] = True

                placement_map.append({
                    'curriculum':   entry,
                    'date':         date,
                    'slot':         slot,
                    'venue':        venue,
                    'invigilator':  invigilator,
                    'exam_type':    exam_type,
                })

                placed = True
                break

        if not placed:
            raise Exception(
                f"Could not place {exam_type} exam for "
                f"{entry.course.course_code} ({entry.Tclass.class_name}) — "
                f"no available slot found. Add more exam dates or venues."
            )

    with transaction.atomic():
        # clear existing exams of this type for the session
        ExamSession.objects.filter(
            curriculum__session=session,
            exam_type=exam_type,
        ).delete()

        # create ExamSession records
        created_sessions = ExamSession.objects.bulk_create([
            ExamSession(
                curriculum=p['curriculum'],
                exam_type=p['exam_type'],
                date=p['date'],
                time_slot=p['slot'],
            )
            for p in placement_map
        ])

        # match created sessions back to placements by index
        exam_venues = [
            ExamVenue(
                exam_session=exam_session,
                venue=p['venue'],
                invigilator=p['invigilator'],
            )
            for exam_session, p in zip(created_sessions, placement_map)
        ]

        ExamVenue.objects.bulk_create(exam_venues)

    return len(created_sessions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_exam_dates(end_date, days_before):
    """
    Return a list of weekday dates starting from
    (end_date - days_before) up to end_date.
    Excludes weekends.
    """
    import datetime

    start = end_date - datetime.timedelta(days=days_before)
    dates = []
    current = start

    while current <= end_date:
        if current.weekday() < 5:  # 0=Mon, 4=Fri
            dates.append(current)
        current += datetime.timedelta(days=1)

    return dates


def _find_free_venue(venues, venue_busy, date, slot):
    """Return first Venue not booked at this date+slot."""
    for venue in venues:
        if not venue_busy.get((venue.pk, date, slot)):
            return venue
    return None


def _find_invigilator(preferred, all_lecturers, invig_busy, date, slot):
    """
    Return a free invigilator.
    Prefer the course's own professors first (they know the material),
    fall back to any free lecturer.
    """
    for lecturer in preferred:
        if not invig_busy.get((lecturer.pk, date, slot)):
            return lecturer

    for lecturer in all_lecturers:
        if not invig_busy.get((lecturer.pk, date, slot)):
            return lecturer

    return None
