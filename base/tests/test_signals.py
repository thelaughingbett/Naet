
# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.test import TestCase

from base.models import Curriculum, Session, Student


from django.test import TestCase

from .factories import UserFactory


class PostSaveSignalTest(TestCase):

    def test_signal_fires_on_create(self):
        """Example: profile is auto-created when a user is saved."""
        user = UserFactory()
        # assert the side effect of your signal
        # e.g. self.assertTrue(hasattr(user, 'some_profile'))

    def test_signal_does_not_fire_on_update(self):
        """Example: profile is not duplicated on subsequent saves."""
        user = UserFactory()
        user.first_name = 'Updated'
        user.save()
        # assert count is still 1, not 2


class AutoEnrollSignalTest(TestCase):

    def test_core_courses_enrolled_on_student_creation(self):
        # create active session and core curriculum first
        session = Session.objects.create(is_active=True)
        curriculum = Curriculum.objects.create(
            course=self.core_course,
            Tclass=self.tclass,
            session=session
        )

        # create student — signal should fire
        student = Student.objects.create(
            user=self.user,
            class_entered=self.tclass,

        )

        self.assertIn(curriculum, student.enrollments.all())

    def test_no_enrollment_without_active_session(self):
        Session.objects.all().update(is_active=False)

        student = Student.objects.create(
            user=self.user,
            class_entered=self.tclass,

        )

        self.assertEqual(student.enrollments.count(), 0)
