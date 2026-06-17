"""
Test suite for `generate_timetable`, with emphasis on Common Unit (CC)
scheduling.

Adjust the two import lines below to match your project layout:

    from base.models import Timetable
    from base.services.timetable import generate_timetable

and point the factories import at wherever the factories module
(SessionFactory, TclassFactory, CourseFactory, CommonUnitCourseFactory,
CurriculumFactory, LecturerFactory, VenueFactory, ...) actually lives.

Run with:

    python manage.py test path.to.test_timetable_generation
"""

from django.test import TestCase

from base.models import Timetable  # TODO: adjust import path
from base.services.timetable import generate_timetable  # TODO: adjust import path

from .factories import (  # TODO: adjust import path
    SessionFactory,
    TclassFactory,
    CourseFactory,
    CommonUnitCourseFactory,
    CurriculumFactory,
    LecturerFactory,
    VenueFactory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_professors(entry):
    """Remove all lecturers from a curriculum entry (factory always adds a
    default one via post_generation, so this has to be done after creation)."""
    entry.professor.clear()
    return entry


# ---------------------------------------------------------------------------
# Guard rails / input validation
# ---------------------------------------------------------------------------

class GenerationGuardRailsTests(TestCase):

    def test_no_venues_raises(self):
        session = SessionFactory()
        CurriculumFactory(session=session)

        self.assertRaisesMessage(
            Exception, "No venues found", generate_timetable, session
        )

    def test_regular_course_without_professor_raises(self):
        session = SessionFactory()
        VenueFactory()

        entry = CurriculumFactory(session=session)
        _clear_professors(entry)

        self.assertRaisesMessage(
            Exception, "has no assigned professor", generate_timetable, session
        )


# ---------------------------------------------------------------------------
# Regular (non-CC) course scheduling
# ---------------------------------------------------------------------------

class RegularCourseSchedulingTests(TestCase):

    def test_regular_course_placed_at_first_available_slot(self):
        session = SessionFactory()
        venue = VenueFactory()
        entry = CurriculumFactory(session=session)

        created = generate_timetable(session)
        self.assertEqual(created, 1)

        row = Timetable.objects.get(curriculum=entry)
        self.assertEqual(row.day, "MON")
        self.assertEqual(row.time_slot, "08:00-10:00")
        self.assertEqual(row.venue, venue)

    def test_class_day_cap_of_three_is_enforced(self):
        """A single class cannot receive more than 3 sessions on the same
        day - the 4th course for that class must roll over to a new day."""
        session = SessionFactory()
        VenueFactory.create_batch(5)

        tclass = TclassFactory()
        entries = [
            CurriculumFactory(Tclass=tclass, session=session,
                              course=CourseFactory())
            for _ in range(4)
        ]

        created = generate_timetable(session)
        self.assertEqual(created, 4)

        rows = Timetable.objects.filter(curriculum__in=entries)
        mon_rows = [r for r in rows if r.day == "MON"]
        other_rows = [r for r in rows if r.day != "MON"]

        self.assertEqual(len(mon_rows), 3)
        self.assertEqual(len(other_rows), 1)

    def test_placement_fails_once_weekly_capacity_is_exhausted(self):
        """With a 3-slots/day cap over 5 weekdays, a class tops out at 15
        sessions/week. The 16th course for that class should raise a
        descriptive error rather than silently dropping or overbooking."""
        session = SessionFactory()
        VenueFactory.create_batch(5)

        tclass = TclassFactory()
        for _ in range(15):
            CurriculumFactory(Tclass=tclass, session=session,
                              course=CourseFactory())

        overflow_course = CourseFactory(course_code="OVERFLOW1")
        CurriculumFactory(Tclass=tclass, session=session,
                          course=overflow_course)

        self.assertRaisesMessage(
            Exception, "Could not place OVERFLOW1", generate_timetable, session
        )


# ---------------------------------------------------------------------------
# Common Unit (CC) scheduling - the main focus
# ---------------------------------------------------------------------------

class CommonUnitSchedulingTests(TestCase):

    def test_common_unit_lands_on_same_slot_with_distinct_venues(self):
        """The core CC contract: every class taking the common unit gets the
        same day/time slot, but its own venue."""
        session = SessionFactory()
        VenueFactory.create_batch(3)

        cc_course = CommonUnitCourseFactory()
        tclasses = TclassFactory.create_batch(3)
        entries = [
            CurriculumFactory(course=cc_course, Tclass=tclass, session=session)
            for tclass in tclasses
        ]

        created = generate_timetable(session)
        self.assertEqual(created, 3)

        rows = Timetable.objects.filter(curriculum__in=entries)
        self.assertEqual(rows.count(), 3)

        days_slots = {(r.day, r.time_slot) for r in rows}
        self.assertEqual(len(days_slots), 1,
                         "all classes should share the same slot")

        venue_ids = {r.venue_id for r in rows}
        self.assertEqual(len(venue_ids), 3,
                         "each class should get its own venue")

        curriculum_ids = {r.curriculum_id for r in rows}
        self.assertEqual(curriculum_ids, {e.pk for e in entries})

    def test_common_unit_with_single_enrolled_class(self):
        """Edge case n=1: a CC course with only one class enrolled this
        session should still place correctly (one_venue_each with n=1)."""
        session = SessionFactory()
        VenueFactory.create_batch(1)

        cc_course = CommonUnitCourseFactory()
        entry = CurriculumFactory(
            course=cc_course, Tclass=TclassFactory(), session=session)

        created = generate_timetable(session)
        self.assertEqual(created, 1)

        row = Timetable.objects.get(curriculum=entry)
        self.assertIsNotNone(row.venue)

    def test_common_unit_with_no_professors_anywhere_raises(self):
        session = SessionFactory()
        VenueFactory.create_batch(3)

        cc_course = CommonUnitCourseFactory()
        entries = [
            CurriculumFactory(course=cc_course,
                              Tclass=TclassFactory(), session=session)
            for _ in range(2)
        ]
        for entry in entries:
            _clear_professors(entry)

        self.assertRaisesMessage(
            Exception, "has no assigned professors on any", generate_timetable, session
        )

    def test_common_unit_insufficient_venues_raises(self):
        """3 classes need 3 distinct venues at the chosen slot; with only 2
        venues in the system, no slot can ever satisfy that, so generation
        should fail with a clear error."""
        session = SessionFactory()
        VenueFactory.create_batch(2)

        cc_course = CommonUnitCourseFactory()
        for _ in range(3):
            CurriculumFactory(course=cc_course,
                              Tclass=TclassFactory(), session=session)

        self.assertRaisesMessage(
            Exception, "Could not place common unit", generate_timetable, session
        )

    def test_common_unit_respects_class_day_cap(self):
        """If a class involved in a common unit already has 3 sessions on a
        given day (from its regular courses), the common unit cannot be
        scheduled on that day for that class and must roll over."""
        session = SessionFactory()
        VenueFactory.create_batch(4)

        tclass_a = TclassFactory()
        tclass_b = TclassFactory()

        # fill tclass_a's Monday with 3 regular courses (each its own lecturer)
        for _ in range(3):
            CurriculumFactory(Tclass=tclass_a, session=session,
                              course=CourseFactory())

        cc_course = CommonUnitCourseFactory()
        entry_a = CurriculumFactory(
            course=cc_course, Tclass=tclass_a, session=session)
        entry_b = CurriculumFactory(
            course=cc_course, Tclass=tclass_b, session=session)

        generate_timetable(session)

        row_a = Timetable.objects.get(curriculum=entry_a)
        row_b = Timetable.objects.get(curriculum=entry_b)

        self.assertNotEqual(row_a.day, "MON")
        self.assertEqual((row_a.day, row_a.time_slot),
                         (row_b.day, row_b.time_slot))

    def test_lecturer_shared_across_common_unit_classes(self):
        """The same lecturer may teach the common unit for more than one
        class. They'll appear twice in the combined professor list - this
        should not error, and the unit should still place normally."""
        session = SessionFactory()
        VenueFactory.create_batch(2)

        shared_lecturer = LecturerFactory()
        cc_course = CommonUnitCourseFactory()

        entries = [
            CurriculumFactory(
                course=cc_course,
                Tclass=TclassFactory(),
                session=session,
                professors=[shared_lecturer],
            )
            for _ in range(2)
        ]

        created = generate_timetable(session)
        self.assertEqual(created, 2)

        rows = Timetable.objects.filter(curriculum__in=entries)
        days_slots = {(r.day, r.time_slot) for r in rows}
        self.assertEqual(len(days_slots), 1)

    def test_busy_lecturer_on_one_class_blocks_the_whole_common_unit_slot(self):
        """Regular courses are scheduled first. If a lecturer involved in
        ANY class of a common unit is already busy at a slot, the entire
        common unit is pushed to a different slot - even if the *other*
        class's lecturer would have been free.

        This documents current behaviour: availability for a CC slot is
        the union of all involved lecturers' availability, not a
        per-class check. Worth confirming this matches the intended
        scheduling policy.
        """
        session = SessionFactory()
        VenueFactory.create_batch(3)

        busy_lecturer = LecturerFactory()
        free_lecturer = LecturerFactory()

        # regular course takes the very first slot and occupies busy_lecturer
        CurriculumFactory(
            Tclass=TclassFactory(),
            session=session,
            course=CourseFactory(),
            professors=[busy_lecturer],
        )

        cc_course = CommonUnitCourseFactory()
        entry_a = CurriculumFactory(
            course=cc_course, Tclass=TclassFactory(), session=session,
            professors=[busy_lecturer],
        )
        entry_b = CurriculumFactory(
            course=cc_course, Tclass=TclassFactory(), session=session,
            professors=[free_lecturer],
        )

        generate_timetable(session)

        regular_row = Timetable.objects.get(
            curriculum__course__course_type="C")
        cc_rows = Timetable.objects.filter(curriculum__in=[entry_a, entry_b])

        self.assertEqual(
            (regular_row.day, regular_row.time_slot), ("MON", "08:00-10:00"))

        cc_days_slots = {(r.day, r.time_slot) for r in cc_rows}
        self.assertEqual(len(cc_days_slots), 1)
        cc_slot = next(iter(cc_days_slots))
        self.assertNotEqual(cc_slot, (regular_row.day, regular_row.time_slot))

    def test_partial_professor_assignment_does_not_raise(self):
        """If only SOME classes on a common unit have an assigned
        professor, the unit is still scheduled for ALL classes - including
        the one with zero professors of its own.

        This documents current behaviour: the "no assigned professors"
        guard only fires when *every* class on the unit has none. Flagging
        in case the intent was per-class enforcement.
        """
        session = SessionFactory()
        VenueFactory.create_batch(2)

        cc_course = CommonUnitCourseFactory()
        entry_with_prof = CurriculumFactory(
            course=cc_course, Tclass=TclassFactory(), session=session)
        entry_without_prof = CurriculumFactory(
            course=cc_course, Tclass=TclassFactory(), session=session)
        _clear_professors(entry_without_prof)

        created = generate_timetable(session)
        self.assertEqual(created, 2)

        rows = Timetable.objects.filter(
            curriculum__in=[entry_with_prof, entry_without_prof])
        days_slots = {(r.day, r.time_slot) for r in rows}
        self.assertEqual(len(days_slots), 1)

    def test_multiple_distinct_common_units_each_get_own_consistent_slot(self):
        session = SessionFactory()
        VenueFactory.create_batch(3)

        cc_course_1 = CommonUnitCourseFactory()
        cc_course_2 = CommonUnitCourseFactory()

        entries_1 = [
            CurriculumFactory(course=cc_course_1,
                              Tclass=TclassFactory(), session=session)
            for _ in range(2)
        ]
        entries_2 = [
            CurriculumFactory(course=cc_course_2,
                              Tclass=TclassFactory(), session=session)
            for _ in range(2)
        ]

        created = generate_timetable(session)
        self.assertEqual(created, 4)

        for entries in (entries_1, entries_2):
            rows = Timetable.objects.filter(curriculum__in=entries)
            days_slots = {(r.day, r.time_slot) for r in rows}
            self.assertEqual(len(days_slots), 1)
            venue_ids = {r.venue_id for r in rows}
            self.assertEqual(len(venue_ids), 2)


# ---------------------------------------------------------------------------
# Regeneration and session isolation
# ---------------------------------------------------------------------------

class RegenerationAndIsolationTests(TestCase):

    def test_regenerating_same_session_does_not_duplicate(self):
        session = SessionFactory()
        VenueFactory.create_batch(3)
        CurriculumFactory(session=session)

        first_count = generate_timetable(session)
        second_count = generate_timetable(session)

        self.assertEqual(first_count, second_count)
        self.assertEqual(
            Timetable.objects.filter(
                curriculum__session=session).count(), second_count
        )

    def test_other_sessions_timetable_is_untouched(self):
        session_a = SessionFactory()
        session_b = SessionFactory()
        VenueFactory.create_batch(3)

        CurriculumFactory(session=session_a)
        CurriculumFactory(session=session_b)

        generate_timetable(session_a)
        count_a = Timetable.objects.filter(
            curriculum__session=session_a).count()

        generate_timetable(session_b)

        self.assertEqual(
            Timetable.objects.filter(
                curriculum__session=session_a).count(), count_a
        )


# ---------------------------------------------------------------------------
# Mixed integration scenario
# ---------------------------------------------------------------------------

class IntegrationTests(TestCase):

    def test_mixed_regular_and_common_unit_session(self):
        session = SessionFactory()
        VenueFactory.create_batch(4)

        regular_entries = [CurriculumFactory(
            session=session) for _ in range(2)]

        cc_course = CommonUnitCourseFactory()
        cc_entries = [
            CurriculumFactory(course=cc_course,
                              Tclass=TclassFactory(), session=session)
            for _ in range(2)
        ]

        total = len(regular_entries) + len(cc_entries)
        created = generate_timetable(session)

        self.assertEqual(created, total)
        self.assertEqual(
            Timetable.objects.filter(
                curriculum__session=session).count(), total
        )
