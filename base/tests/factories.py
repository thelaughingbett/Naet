# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import factory
from factory.django import DjangoModelFactory

from base.models import (
    Department,
    DeptAdmin,
    Lecturer,
    Programme,
    School,
    SchoolAdmin,
    Session,
    Student,
    Tclass,
    User,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True


class SchoolFactory(DjangoModelFactory):
    class Meta:
        model = School

    name = factory.Sequence(lambda n: f'School {n}')


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    name = factory.Sequence(lambda n: f'Department {n}')
    school = factory.SubFactory(SchoolFactory)


class ProgrammeFactory(DjangoModelFactory):
    class Meta:
        model = Programme

    programme_name = factory.Sequence(lambda n: f'Programme {n}')
    department = factory.SubFactory(DepartmentFactory)


class TclassFactory(DjangoModelFactory):
    class Meta:
        model = Tclass

    class_name = factory.Sequence(lambda n: f'Class {n}')
    programme = factory.SubFactory(ProgrammeFactory)


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = Session

    academic_year = factory.Sequence(lambda n: f'202{n}/202{n+1}')
    semester = 1
    is_active = False


class StudentFactory(DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(UserFactory)
    class_entered = factory.SubFactory(TclassFactory)


class LecturerFactory(DjangoModelFactory):
    class Meta:
        model = Lecturer

    user = factory.SubFactory(UserFactory)
    department = factory.SubFactory(DepartmentFactory)


class SchoolAdminFactory(DjangoModelFactory):
    class Meta:
        model = SchoolAdmin

    user = factory.SubFactory(UserFactory)
    school = factory.SubFactory(SchoolFactory)


class DeptAdminFactory(DjangoModelFactory):
    class Meta:
        model = DeptAdmin

    user = factory.SubFactory(UserFactory)
    department = factory.SubFactory(DepartmentFactory)
