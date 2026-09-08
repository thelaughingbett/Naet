# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
from django.db import models

from ..base import BaseModelMixin
from .isced import UNESCO_ISCED_FIELDS
# FIX: original file called GradingScale.objects.filter(...) inside
# get_grading_scale() with no import anywhere in the module — that
# would raise NameError the first time a Course with no grading_scale
# set tried to resolve its default. get_weighting_scheme() right below
# it did import WeightingScheme (lazily); this brings GradingScale up
# to the same standard, imported at module level since curriculum/
# doesn't import academics/ back (no circularity risk).
from ..curriculum.grading_policy import GradingScale, WeightingScheme

from simple_history.models import HistoricalRecords


class Course(BaseModelMixin):
    """
    Unified University Course Registry. Accommodates Undergraduate,
    Practical-heavy, Experiential, and Postgraduate Research modules.
    """

    type_choices = [
        ("C",  "Core"),
        ("E",  "Elective"),
        ("CC", "Common Unit"),
        ("P", "Practical / Laboratory Unit"),
        ("IA", "Industrial Attachment / Internship"),
        ("TP", "Teaching Practice / Field Practicum"),
        ("PR", "Postgraduate Research Thesis / Dissertation"),
        ("ST", "Specialised Seminar / Independent Study"),
    ]

    course_name = models.CharField(max_length=255)
    course_code = models.CharField(
        unique=True,
        max_length=74,
        help_text="e.g., CCS 401, BIL 810"
    )

    department = models.ForeignKey('Department', on_delete=models.PROTECT)

    course_type = models.CharField(
        choices=type_choices,
        default='C',
        max_length=45,
        db_index=True
    )

    # 2. Base Credit Representation (CUE: 1 Credit = 15 Instructional Hours)
    credits = models.IntegerField(
        default=3,
        help_text="Undergraduate units default to 3 credits. PhD Research can scale up to 15+ credits."
    )

    # 3. Mode Hours Tracking (Required for CUE Curriculum Audits)
    lecture_hours_per_week = models.PositiveIntegerField(default=3)
    practical_hours_per_week = models.PositiveIntegerField(
        default=0,
        help_text="Required if course_type is (Practical/Lab)."
    )

    # 4. Industrial Attachment & Field Experiential Metrics
    attachment_duration_weeks = models.PositiveIntegerField(
        default=0,
        help_text="Mandatory weeks for industrial attach/practicums. Usually 8-12 weeks under CUE guidelines."
    )

    is_externally_assessed = models.BooleanField(
        default=False,
        help_text="Requires an appointed external university assessor/supervisor field-visit grade signoff."
    )

    # 5. Specialized Postgraduate Research Vectors (Masters / PhDs)
    is_postgraduate_only = models.BooleanField(
        default=False,
        help_text="Hard lock variable preventing undergraduate students from registering into this code."
    )

    requires_defense_panel = models.BooleanField(
        default=False,
        help_text="Mandatory for Thesis/Dissertation options. Triggers Senate Board of Examiners appointment workflows."
    )

    expected_competencies = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="List of core skill competencies mapped to this course for UCBEF checks."
    )

    prerequisites = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
    )

    unesco_isced = models.CharField(
        max_length=123,
        null=True,
        choices=UNESCO_ISCED_FIELDS,
        blank=True,
        help_text="Standardized UNESCO tag for this specific subject matter."
    )

    offered = models.IntegerField(
        default=1,
        help_text="Year of study this unit is typically scheduled."
    )

    pass_mark = models.PositiveIntegerField(
        default=40,
        help_text="Minimum score to pass this specific course. Override per "
        "course — e.g. a professional/regulated unit might require 50."
    )

    grading_scale = models.ForeignKey(
        'GradingScale',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Which A/B/C/D/E (or pass/fail) band set applies to this "
        "course's results. Leave blank to use the institution default."
    )

    weighting_scheme = models.ForeignKey(
        'WeightingScheme', on_delete=models.PROTECT, null=True, blank=True,
        related_name='courses',
        help_text="Default CAT/Exam/etc. weighting for this course. Leave "
        "blank to use the institution default scheme."
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Course Module"
        verbose_name_plural = "Course Modules"

    def __str__(self):
        return f"{self.course_code} — {self.course_name} ({self.get_course_type_display()})"

    def clean(self):
        """
        Structural Integrity Middleware: Enforces CUE operational parameters across
        distinct academic unit styles.
        """
        super().clean()

        # Rule A: Industrial Attachment Guardrails
        if self.course_type == 'IA':
            if self.attachment_duration_weeks == 0:
                raise ValidationError({
                    'attachment_duration_weeks': "CUE Academic Guidelines require a defined duration (in weeks) "
                    "for all active Industrial Attachment / Internship models."
                })
            self.lecture_hours_per_week = 0
            self.practical_hours_per_week = 0

        # Rule B: Postgraduate Research (Thesis/Dissertation) Core Controls
        if self.course_type == 'PR':
            self.is_postgraduate_only = True
            self.requires_defense_panel = True
            self.lecture_hours_per_week = 0
            self.practical_hours_per_week = 0

            if self.credits < 6:
                raise ValidationError({
                    'credits': "CUE Thesis Weighting Rule: Postgraduate Research projects must carry substantial credit "
                               "load structures (Minimum 6 credits for Masters, significantly higher for Doctorates)."
                })

        # Rule C: Practical Lab Class Hour Alignments
        if self.course_type == 'P' and self.practical_hours_per_week == 0:
            raise ValidationError({
                'practical_hours_per_week': "Practical/Laboratory course types require assigning continuous weekly lab hours."
            })

    def get_grading_scale(self):
        if self.grading_scale_id:
            return self.grading_scale
        default = GradingScale.objects.filter(is_default=True).first()
        if default is None:
            raise ValidationError(
                f"Course {self.course_code} has no grading_scale set and no "
                f"GradingScale is marked is_default=True — nothing to fall back to."
            )
        return default

    def get_weighting_scheme(self):
        if self.weighting_scheme_id:
            return self.weighting_scheme
        default = WeightingScheme.objects.filter(is_default=True).first()
        if default is None:
            raise ValidationError(
                f"Course {self.course_code} has no weighting_scheme and no "
                f"WeightingScheme is marked is_default=True."
            )
        return default
