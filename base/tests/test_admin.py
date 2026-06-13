from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from base.admin import StudentAdmin
from base.models import Student

# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from .factories import (
    DepartmentFactory,
    DeptAdminFactory,
    SchoolAdminFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)


class ScopedQuerysetTest(TestCase):
    """Ensure each role only sees records they are scoped to."""

    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()

        self.school_a = SchoolFactory()
        self.school_b = SchoolFactory()
        self.dept_a = DepartmentFactory(school=self.school_a)
        self.dept_b = DepartmentFactory(school=self.school_b)

        self.superuser = UserFactory(is_superuser=True, is_staff=True)
        self.school_admin = SchoolAdminFactory(school=self.school_a).user
        self.dept_admin = DeptAdminFactory(department=self.dept_a).user

        self.student_a = StudentFactory()  # in school_a via factory chain
        self.student_b = StudentFactory()  # in school_b via factory chain

    def _request(self, user):
        request = self.factory.get('/')
        request.user = user
        return request

    def test_superuser_sees_all_students(self):
        from base.admin.users import StudentAdmin
        from base.models import Student

        ma = StudentAdmin(Student, self.site)
        qs = ma.get_queryset(self._request(self.superuser))
        self.assertEqual(qs.count(), Student.objects.count())

    def test_school_admin_scoped_to_own_school(self):
        from base.admin.users import StudentAdmin
        from base.models import Student

        ma = StudentAdmin(Student, self.site)
        qs = ma.get_queryset(self._request(self.school_admin))
        for student in qs:
            self.assertEqual(
                student.class_entered.programme.department.school,
                self.school_a
            )

    def test_unauthenticated_role_sees_nothing(self):
        from base.admin.users import StudentAdmin
        from base.models import Student

        bare_user = UserFactory()  # no profile attached
        ma = StudentAdmin(Student, self.site)
        qs = ma.get_queryset(self._request(bare_user))
        self.assertEqual(qs.count(), 0)


class StudentAdminTest(TestCase):

    def setUp(self):
        self.site = AdminSite()
        self.admin = StudentAdmin(Student, self.site)
        self.request = self.client.request().wsgi_request
        self.request.user = self.dept_admin_user

    def test_dept_admin_sees_only_own_department_students(self):
        qs = self.admin.get_queryset(self.request)
        for student in qs:
            self.assertEqual(
                student.class_entered.programme.department,
                self.dept_admin_user.deptadmin_profile.department
            )
