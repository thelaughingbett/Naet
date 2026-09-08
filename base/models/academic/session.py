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

from ..base import BaseModelMixin


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

    registration_start = models.DateField(null=True, blank=True)
    registration_end = models.DateField(null=True, blank=True)

    # is this redundant given that active session is set in school ? 👇🏿
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
        # Session now lives in academics/, Curriculum lives in
        # curriculum/curriculum.py — up one level out of academics/,
        # back down into the sibling curriculum package.
        from ..curriculum.curriculum import Curriculum

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
