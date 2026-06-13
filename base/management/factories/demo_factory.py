# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from base.models import FeeStructure
from .factories import TclassFactory, SessionFactory
from django.db.models.signals import post_save
from datetime import date
from datetime import datetime
import random
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

    name = factory.Iterator([
        'School of Engineering & Architecture',
        'School of Computing & Informatics',
        'School of Business & Economics',
        'School of Health Sciences',
        'School of Law & Social Sciences',
        'School of Pure & Applied Sciences',
    ])


class SchoolFactory(DjangoModelFactory):
    class Meta:
        model = School

    name = factory.Iterator([
        'School of Engineering & Architecture',
        'School of Computing & Informatics',
        'School of Business & Economics',
        'School of Health Sciences',
    ])


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    school = factory.SubFactory(SchoolFactory)

    @factory.lazy_attribute
    def name(self):
        # Mapping dict connecting parent school names to realistic department lists
        mapping = {
            'School of Engineering & Architecture': [
                'Department of Civil Engineering',
                'Department of Mechanical Engineering',
                'Department  of Electrical Engineering'
            ],
            'School of Computing & Informatics': [
                'Department of Computer Science',
                'Department of Information Technology',
                'Department of Software Engineering'
            ],
            'School of Business & Economics': [
                'Department of Accounting & Finance',
                'Department of Business Administration',
                'Department of Economics'
            ],
            'School of Health Sciences': [
                'Department of Nursing',
                'Department of Public Health',
                'Department of Clinical Medicine'
            ]
        }

        school_name = self.school.name

        if school_name in mapping:
            return random.choice(mapping[school_name])

        return f"Department of General Studies"


class ProgrammeFactory(DjangoModelFactory):
    class Meta:
        model = Programme

    department = factory.SubFactory(DepartmentFactory)

    @factory.lazy_attribute
    def programme_name(self):
        # Mapping dictionary connecting department names to realistic academic programmes
        mapping = {
            'Department of Civil Engineering': [
                'Bachelor of Science in Civil Engineering',
                'Diploma in Civil Engineering'
            ],
            'Department of Mechanical Engineering': [
                'Bachelor of Science in Mechanical Engineering',
                'Bachelor of Technology in Mechanical Systems'
            ],
            'Department  of Electrical Engineering': [
                'Bachelor of Science in Electrical & Electronic Engineering',
                'Diploma in Electrical Engineering'
            ],
            'Department of Computer Science': [
                'Bachelor of Science in Computer Science',
                'Master of Science in Computer Science'
            ],
            'Department of Information Technology': [
                'Bachelor of Science in Information Technology',
                'Bachelor of Business Information Technology'
            ],
            'Department of Software Engineering': [
                'Bachelor of Science in Software Engineering'
            ],
            'Department of Accounting & Finance': [
                'Bachelor of Commerce (Accounting Option)',
                'Bachelor of Science in Finance'
            ],
            'Department of Business Administration': [
                'Bachelor of Business Administration',
                'Master of Business Administration (MBA)'
            ],
            'Department of Economics': [
                'Bachelor of Science in Economics & Statistics',
                'Bachelor of Economics'
            ],
            'Department of Nursing': [
                'Bachelor of Science in Nursing'
            ],
            'Department of Public Health': [
                'Bachelor of Science in Public Health'
            ],
            'Department of Clinical Medicine': [
                'Bachelor of Science in Clinical Medicine'
            ]
        }

        # Access the name of the department instance assigned to this programme
        dept_name = self.department.name

        # Pull a matching program name, or fall back to a safe fallback sequence
        if dept_name in mapping:
            return random.choice(mapping[dept_name])

        return f"Bachelor of Arts in General Studies"


class TclassFactory(DjangoModelFactory):
    class Meta:
        model = Tclass

    programme = factory.SubFactory(ProgrammeFactory)

    # Track created class identifiers in-memory to prevent duplicates
    _created_classes = set()

    @factory.lazy_attribute
    def class_name(self):
        # 1. Base code prefix map based on your programmes
        prefix_mapping = {
            'Bachelor of Science in Computer Science': 'COM',
            'Bachelor of Science in Information Technology': 'BIT',
            'Bachelor of Science in Software Engineering': 'SWE',
            'Bachelor of Science in Civil Engineering': 'CIV',
            'Bachelor of Science in Mechanical Engineering': 'MEC',
            'Bachelor of Science in Electrical & Electronic Engineering': 'EEE',
            'Bachelor of Commerce (Accounting Option)': 'ACC',
            'Bachelor of Science in Finance': 'FIN',
            'Bachelor of Business Administration': 'BBA',
            'Bachelor of Science in Economics & Statistics': 'ECO',
            'Bachelor of Science in Nursing': 'NUR',
            'Bachelor of Science in Public Health': 'BPH',
            'Bachelor of Science in Clinical Medicine': 'CLM',
        }

        # Look up the code prefix, default to 'GEN' if program isn't found
        prog_name = self.programme.programme_name
        prefix = prefix_mapping.get(prog_name, 'GEN')

        # 2. Get the short 2-digit format of the current year (e.g., 2026 -> '26')
        current_year_short = datetime.now().strftime('%y')

        # 3. Track and generate unique cohorts using a suffix loop
        suffix = 1
        while True:
            # First variation is just "COM/26", subsequent are "COM/26-A", "COM/26-B", etc.
            if suffix == 1:
                potential_name = f"{prefix}/{current_year_short}"
            else:
                # Use alphabet letters for multiple streams of the same year intake
                # 2 gives 'A', 3 gives 'B', etc.
                stream_letter = chr(63 + suffix)
                potential_name = f"{prefix}/{current_year_short}-{stream_letter}"

            # If this precise code hasn't been used yet, claim it
            if potential_name not in TclassFactory._created_classes:
                TclassFactory._created_classes.add(potential_name)
                return potential_name

            suffix += 1


class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Session

    # In-memory tracking state variables
    _current_year = 2025       # Start tracking year from 2025
    _current_trimester = 0     # Will advance to 1 on first run

    @classmethod
    def _advance_trimester_timeline(cls):
        """Advances the trimester cycle and increments calendar years sequentially"""
        cls._current_trimester += 1
        if cls._current_trimester > 3:
            cls._current_trimester = 1
            cls._current_year += 1

    @factory.lazy_attribute
    def academic_year(self):
        # Step the global timeline forward for this factory run
        SessionFactory._advance_trimester_timeline()
        next_year = SessionFactory._current_year + 1
        return f"{SessionFactory._current_year}/{next_year}"

    @factory.lazy_attribute
    def semester(self):
        return SessionFactory._current_trimester

    @factory.lazy_attribute
    def start_date(self):
        # Calculate start dates based on the 4-month academic window partitions
        year = SessionFactory._current_year
        if SessionFactory._current_trimester == 1:
            return date(year, 9, 1)        # Trimester 1: Sept - Dec
        elif SessionFactory._current_trimester == 2:
            # Trimester 2: Jan - Apr (rolls to next calendar year)
            return date(year + 1, 1, 1)
        else:
            return date(year + 1, 5, 1)    # Trimester 3: May - Aug

    @factory.lazy_attribute
    def end_date(self):
        year = SessionFactory._current_year
        if SessionFactory._current_trimester == 1:
            return date(year, 12, 31)
        elif SessionFactory._current_trimester == 2:
            return date(year + 1, 4, 30)
        else:
            return date(year + 1, 8, 31)

    @factory.lazy_attribute
    def is_active(self):
        # Default all entries to False initially; post_generation fixes the last one
        return False

    @factory.post_generation
    def set_only_latest_active(obj, create, extracted, **kwargs):
        """
        Post-generation hook that ensures only the absolute newest 
        session in the database remains active.
        """
        if not create:
            return

        # Deactivate all past historical sessions
        Session.objects.exclude(id=obj.id).update(is_active=False)

        # Turn the brand new session on
        obj.is_active = True
        obj.save()


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


class FeeStructureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeeStructure

    Tclass = factory.SubFactory(TclassFactory)
    session = factory.SubFactory(SessionFactory)

    @factory.lazy_attribute
    def breakdown(self):
        # Access the trimester number from the linked session instance
        trimester = self.session.semester

        # Base tuition fee remains constant across terms
        base_tuition = 45000.00
        hostel_fee = 12000.00

        if trimester == 1:
            # Trimester 1: Full admission + administrative overhead charges
            return {
                'tuition': base_tuition,
                'registration': 5000.00,
                'hostel': hostel_fee,
                'medical_levy': 3000.00,
                'student_activity': 2000.00,
                'library': 1500.00
            }
        elif trimester == 2:
            # Trimester 2: Standard tuition, hostel, and minor continuous asset upkeep fees
            return {
                'tuition': base_tuition,
                'registration': 0.00,  # No registration fee mid-year
                'hostel': hostel_fee,
                'library': 1500.00,
                'examination_fee': 2000.00
            }
        else:
            # Trimester 3: Often a shorter or standard term, lower administrative overhead
            return {
                'tuition': base_tuition,
                'registration': 0.00,
                'hostel': hostel_fee,
                'examination_fee': 2000.00
            }
