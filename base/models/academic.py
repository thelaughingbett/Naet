# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import datetime
import re

from django.db import models, transaction


from .base import BaseModelMixin, WithDepartmentMixin, WithSchoolMixin


class Institution(BaseModelMixin):
    active_session = models.ForeignKey(
        'Session',
        on_delete=models.DO_NOTHING
    )

    institution_name = models.CharField(max_length=123)
    logo = models.ImageField(upload_to='logo/')

    class Meta:
        abstract = True


class School(BaseModelMixin):
    school_name = models.CharField(max_length=78)

    active_session = models.ForeignKey(
        'Session',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"school of {self.school_name}"


class Department(WithSchoolMixin, BaseModelMixin):
    department_name = models.CharField(max_length=123)

    def __str__(self):
        return f"Department of {self.department_name}"


class Programme(BaseModelMixin, WithDepartmentMixin):
    kenyan_degrees = [
        ("BSc",    "Bachelor of Science"),
        ("BEd",    "Bachelor of Education"),
        ("LLB",    "Bachelor of Laws"),
        ("BA",     "Bachelor of Arts"),
        ("BCom",   "Bachelor of Commerce"),
        ("BBIT",   "Bachelor of Business Information Technology"),
        ("B.Arch", "Bachelor of Architecture"),
        ("BEng",   "Bachelor of Engineering"),
        ("MBChB",  "Bachelor of Medicine and Bachelor of Surgery"),
        ("BPharm", "Bachelor of Pharmacy"),
        ("BDS",    "Bachelor of Dental Surgery"),
        ("PGDE",   "Post Graduate Diploma in Education"),
        ("MSc",    "Master of Science"),
        ("MA",     "Master of Arts"),
        ("MBA",    "Master of Business Administration"),
        ("LLM",    "Master of Laws"),
        ("MEd",    "Master of Education"),
        ("MPH",    "Master of Public Health"),
        ("PhD",    "Doctor of Philosophy"),
        ("MD",     "Doctor of Medicine"),
    ]

    degree_type = models.CharField(max_length=123, choices=kenyan_degrees)
    programme_name = models.CharField(max_length=100)

    current_class = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        related_name='current_class',
        null=True,
        blank=True
    )

    duration_years = models.IntegerField(default=4)
    semesters_per_year = models.IntegerField(default=2)

    @property
    def total_semesters(self):
        return self.duration_years * self.semesters_per_year

    def __str__(self):
        return self.programme_name


class Tclass(BaseModelMixin):
    class_name = models.CharField(max_length=78)

    programme = models.ForeignKey('Programme', on_delete=models.PROTECT)

    courses = models.ManyToManyField('Course', through='Curriculum')

    year_of_study = models.IntegerField(default=1, null=True, blank=True)

    graduated = models.DateField(null=True)

    def __str__(self):
        return self.class_name


class Session(BaseModelMixin):
    SEMESTER_CHOICES = [
        ("1", "Semester 1"),
        ("2", "Semester 2"),
        ("3", "Semester 3"),
    ]

    academic_year = models.CharField(max_length=9)  # e.g. "2024/2025"
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('academic_year', 'semester')

    def __str__(self):
        return f"{self.academic_year} - Sem {self.semester}"

    @property
    def progress(self):
        today = datetime.datetime.now().date()
        if today <= self.start_date:
            return 0
        if today >= self.end_date:
            return 100
        total_days = (self.end_date - self.start_date).days
        days_passed = (today - self.start_date).days
        if total_days <= 0:
            return 100
        return round((days_passed / total_days) * 100)

    def generate_next_session_name(self):
        year = self.academic_year
        session = self.semester
        year_match = re.search(r'(\d{4})/(\d{4})', year)
        start_date = self.start_date + datetime.timedelta(days=1)
        current_sem = int(session)

        if current_sem < len(self.SEMESTER_CHOICES):
            next_sem = current_sem + 1
            next_year_string = year
        else:
            next_sem = 1
            if year_match:
                start_yr = int(year_match.group(1)) + 1
                end_year = int(year_match.group(2)) + 1
                next_year_string = f"{start_yr}/{end_year}"
            else:
                next_year_string = " "

        return (next_sem, start_date, next_year_string)

    @classmethod
    def rollover_academic_session(cls, keep_professor=True):
        from .curriculum import Curriculum

        with transaction.atomic():
            current_session = cls.objects.get(is_active=True)
            next_sem, start_date, next_year = current_session.generate_next_session_name()

            next_session, created = cls.objects.get_or_create(
                academic_year=next_year,
                semester=next_sem,
                is_active=True,
                start_date=start_date
            )

            session_prev = cls.objects.get(
                semester=next_sem,
                academic_year=current_session.academic_year
            )

            cloned_count = Curriculum.clone_curriculum(
                from_session_id=session_prev.record_id,
                to_session_id=next_session.record_id
            )

            current_session.is_active = False
            current_session.save()
            next_session.is_active = True
            next_session.save()

            return next_session, cloned_count


class Course(BaseModelMixin):
    type_choices = [
        ("C",  "Core"),
        ("E",  "Elective"),
        ("CC", "Common Unit"),
    ]

    course_name = models.CharField(max_length=255)
    course_code = models.CharField(unique=True, max_length=74)

    department = models.ForeignKey('Department', on_delete=models.PROTECT)

    course_type = models.CharField(
        choices=type_choices, default='C', max_length=45)

    credits = models.IntegerField(default=3)

    prerequisites = models.ManyToManyField("self", blank=True)

    offered = models.IntegerField(default=1)

    def __str__(self):
        return self.course_code
