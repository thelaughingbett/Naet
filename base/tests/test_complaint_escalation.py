# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Tests for the escalation layer in base/models/complaints.py.

Run with: python manage.py test base.tests.test_complaint_escalation

Uses Django's TestCase (transactional per-test rollback) rather than
pytest. setUp() builds a minimal Student + staff User — swap the
field names in _create_student()/_create_staff_user() for whatever
your actual Student/User models require; I don't have their full
field lists from what's been shared so far, only that Complaint FKs
to 'Student' and 'User' by string reference.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from base.models import Complaint, ComplaintEscalationHistory, Student

User = get_user_model()


def _create_student():
    user = User.objects.create_user(
        username='student1', email='student1@example.com', password='x'
    )
    # Adjust these kwargs to match your actual Student model fields.
    return Student.objects.create(user=user)


def _create_staff_user():
    return User.objects.create_user(
        username='staff1', email='staff1@example.com', password='x'
    )


class ComplaintEscalationTestCase(TestCase):
    """Base class that sets up a student, a staff user, and one
    Facilities-category complaint every subclass can reuse."""

    def setUp(self):
        self.student = _create_student()
        self.staff_user = _create_staff_user()
        self.complaint = Complaint.objects.create(
            student=self.student,
            category='Facilities',
            subject='Broken shower',
            description='No hot water in block C for a week.',
        )


class HarassmentComplaintTestCase(TestCase):
    """Separate setUp since Harassment starts at a different level
    and forces priority — keeping it out of the shared base avoids
    every other test class implicitly depending on this special case."""

    def setUp(self):
        self.student = _create_student()
        self.complaint = Complaint.objects.create(
            student=self.student,
            category='Harassment',
            subject='Reported incident',
            description='Details withheld in this test.',
        )

    def test_starts_at_student_affairs(self):
        self.assertEqual(self.complaint.current_level, 'StudentAffairs')

    def test_priority_forced_critical(self):
        self.assertEqual(self.complaint.priority, 'Critical')


class InitialStateTests(ComplaintEscalationTestCase):

    def test_current_level_set_on_creation(self):
        # Facilities path starts at 'School' (the rep), not 'Department'.
        self.assertEqual(self.complaint.current_level, 'School')

    def test_sla_due_at_set_on_creation(self):
        self.assertIsNotNone(self.complaint.sla_due_at)
        self.assertGreater(self.complaint.sla_due_at, timezone.now())


class ManualEscalationTests(ComplaintEscalationTestCase):

    def test_requires_a_user(self):
        with self.assertRaises(ValidationError):
            self.complaint.escalate(automatic=False, by_user=None)

    def test_advances_to_next_level(self):
        self.complaint.escalate(by_user=self.staff_user,
                                reason="Rep didn't respond")
        self.assertEqual(self.complaint.current_level, 'StudentAffairs')

    def test_status_becomes_escalated(self):
        self.complaint.escalate(by_user=self.staff_user, reason="test")
        self.assertEqual(self.complaint.status, 'Escalated')

    def test_history_row_is_not_automatic(self):
        history = self.complaint.escalate(
            by_user=self.staff_user, reason="test")
        self.assertFalse(history.is_automatic)
        self.assertEqual(history.escalated_by, self.staff_user)

    def test_priority_untouched_without_explicit_new_priority(self):
        original = self.complaint.priority
        self.complaint.escalate(by_user=self.staff_user, reason="test")
        self.assertEqual(self.complaint.priority, original)

    def test_priority_set_when_caller_passes_new_priority(self):
        self.complaint.escalate(by_user=self.staff_user,
                                reason="test", new_priority='High')
        self.assertEqual(self.complaint.priority, 'High')

    def test_sla_due_at_extended_on_escalation(self):
        before = self.complaint.sla_due_at
        self.complaint.escalate(by_user=self.staff_user, reason="test")
        self.assertGreater(self.complaint.sla_due_at, before)


class AutomaticEscalationTests(ComplaintEscalationTestCase):

    def test_advances_to_next_level(self):
        self.complaint.escalate(automatic=True)
        self.assertEqual(self.complaint.current_level, 'StudentAffairs')

    def test_history_row_has_no_human_actor(self):
        history = self.complaint.escalate(automatic=True)
        self.assertTrue(history.is_automatic)
        self.assertIsNone(history.escalated_by)

    def test_priority_auto_bumps(self):
        self.assertEqual(self.complaint.priority, 'Medium')  # model default
        self.complaint.escalate(automatic=True)
        self.assertEqual(self.complaint.priority, 'High')

    def test_priority_caps_at_critical(self):
        self.complaint.priority = 'Critical'
        self.complaint.save(update_fields=['priority'])
        self.complaint.escalate(automatic=True)
        self.assertEqual(self.complaint.priority, 'Critical')


class TopOfLadderTests(ComplaintEscalationTestCase):

    def test_escalating_past_senate_returns_none(self):
        # Facilities path: School -> StudentAffairs -> Senate (3 levels)
        self.complaint.escalate(automatic=True)   # School -> StudentAffairs
        self.complaint.escalate(automatic=True)   # StudentAffairs -> Senate
        result = self.complaint.escalate(automatic=True)  # already at Senate
        self.assertIsNone(result)
        self.assertEqual(self.complaint.current_level, 'Senate')

    def test_no_duplicate_history_row_created_at_top(self):
        self.complaint.escalate(automatic=True)
        self.complaint.escalate(automatic=True)
        count_before = self.complaint.escalation_history.count()
        self.complaint.escalate(automatic=True)
        self.assertEqual(
            self.complaint.escalation_history.count(), count_before)

    def test_priority_still_forced_critical_at_top(self):
        # -> StudentAffairs, priority High
        self.complaint.escalate(automatic=True)
        self.complaint.escalate(automatic=True)  # -> Senate, priority Critical
        self.assertEqual(self.complaint.priority, 'Critical')
        self.complaint.escalate(automatic=True)  # stale again at Senate
        # stays capped, no error
        self.assertEqual(self.complaint.priority, 'Critical')


class ComplaintEscalationHistoryValidationTests(ComplaintEscalationTestCase):

    def test_automatic_row_cannot_carry_a_user(self):
        row = ComplaintEscalationHistory(
            complaint=self.complaint,
            escalated_from_level='School',
            escalated_to_level='StudentAffairs',
            escalated_by=self.staff_user,
            is_automatic=True,
            reason_for_escalation="bad row",
        )
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_manual_row_requires_a_user(self):
        row = ComplaintEscalationHistory(
            complaint=self.complaint,
            escalated_from_level='School',
            escalated_to_level='StudentAffairs',
            escalated_by=None,
            is_automatic=False,
            reason_for_escalation="bad row",
        )
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_cannot_escalate_to_same_level(self):
        row = ComplaintEscalationHistory(
            complaint=self.complaint,
            escalated_from_level='School',
            escalated_to_level='School',
            escalated_by=self.staff_user,
            is_automatic=False,
            reason_for_escalation="bad row",
        )
        with self.assertRaises(ValidationError):
            row.full_clean()


class SlaSweepTaskTests(ComplaintEscalationTestCase):

    def test_stale_complaint_gets_escalated(self):
        from base.tasks import escalate_stale_complaints  # adjust import path

        self.complaint.sla_due_at = timezone.now() - timezone.timedelta(hours=1)
        self.complaint.save(update_fields=['sla_due_at'])

        result = escalate_stale_complaints()

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.current_level, 'StudentAffairs')
        self.assertEqual(result['escalated'], 1)
        self.assertEqual(result['failed'], 0)

    def test_resolved_complaint_is_excluded(self):
        from base.tasks import escalate_stale_complaints

        self.complaint.sla_due_at = timezone.now() - timezone.timedelta(hours=1)
        self.complaint.status = 'Resolved'
        self.complaint.resolution_remarks = 'Fixed.'
        self.complaint.save()

        result = escalate_stale_complaints()

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.current_level, 'School')  # untouched
        self.assertEqual(result['escalated'], 0)

    def test_not_yet_due_complaint_is_untouched(self):
        from base.tasks import escalate_stale_complaints

        # sla_due_at is in the future from creation — nothing to do.
        result = escalate_stale_complaints()

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.current_level, 'School')
        self.assertEqual(result['escalated'], 0)
