# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models

from ..base import BaseModelMixin, WithDepartmentMixin
from .isced import UNESCO_ISCED_FIELDS


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

    LEVEL_CHOICES = [
        ("Undergraduate", "Undergraduate"),
        ("Postgraduate",  "Postgraduate"),
        ("Diploma",        "Diploma"),
        ("Certificate",    "Certificate"),
    ]

    STATUS_CHOICES = [
        ("Active",   "Active"),
        ('Expired', 'Expired'),
        ('Suspended', 'Suspended'),
        ('Review', 'Under Review')
    ]

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    programme_name = models.CharField(
        max_length=255,
        unique=True,
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="Undergraduate"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="Active"
    )

    description = models.TextField(
        blank=True,
        default=""
    )

    degree_type = models.CharField(
        max_length=123,
        choices=kenyan_degrees
    )

    current_class = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        related_name='current_class',
        null=True,
        blank=True
    )  # refers to the most recent enrolling class , TODO :  this should change to somehing

    # approved_cue_capacity ,TODO : should be based on accredition or some form of strategy
    capacity = models.IntegerField(default=70)

    # curricula = models.ManyToManyField(
    #     'Course',
    #     through='curricula'
    # )  # an easy way to define curricula for programme and is to be used to define per session curriculum for classes to be defined at creation of programme

    unesco_isced = models.CharField(
        max_length=123,
        null=True,
        blank=True,
        choices=UNESCO_ISCED_FIELDS,
        help_text="Standardized UNESCO tag for this specific subject matter."
    )

    kuccps_programme_code = models.CharField(
        max_length=7,
        unique=True,
        null=True,
        blank=True
    )  # e.g., "1279115"

    duration_years = models.IntegerField(default=4)
    semesters_per_year = models.IntegerField(default=2)
    total_credits_required = models.PositiveIntegerField(default=120)

    @property
    def total_semesters(self):
        return self.duration_years * self.semesters_per_year

    def __str__(self):
        return self.programme_name


class Tclass(BaseModelMixin):
    class_name = models.CharField(max_length=78)

    programme = models.ForeignKey('Programme', on_delete=models.PROTECT)

    # removed: courses = models.ManyToManyField('Syllabus', through='Curriculum')
    # Curriculum is no longer a valid through-model for this — it has no FK
    # to Tclass or Syllabus under the shared-slot design. Use CurriculumClass
    # (which links Tclass -> Syllabus via a specific Curriculum slot) instead.

    year_of_study = models.IntegerField(default=1, blank=True)
    graduated = models.DateField(null=True, blank=True)
    liason = models.ForeignKey(
        'Lecturer', null=True, blank=True, on_delete=models.DO_NOTHING)
    student_rep = models.ForeignKey(
        'Student', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='class_representative'
    )

    @property
    def syllabus_entries(self):
        """Syllabus entries this class is actually scheduled for, via CurriculumClass."""
        from ..curriculum import Syllabus
        return Syllabus.objects.filter(curriculum_links__Tclass=self)

    def __str__(self):
        return self.class_name
