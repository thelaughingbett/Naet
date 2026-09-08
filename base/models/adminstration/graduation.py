# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin

# --- CUE STANDARDIZED GRADUATION CLASSIFICATIONS ---
CLASSIFICATION_CHOICES = [
    ('First_Class', 'First Class Honours / Distinction'),
    ('Second_Upper', 'Second Class Honours (Upper Division)'),
    ('Second_Lower', 'Second Class Honours (Lower Division)'),
    ('Pass', 'Pass (Standard Undergraduate or Postgraduate award)'),
    ('Satisfied', 'Satisfied ( Doctorates/PhDs)'),
]


class DegreeAudit(BaseModelMixin):
    class Result(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        DEFICIENT = "deficient", "Deficient"
        ELIGIBLE = "eligible", "Eligible for Graduation"

    student = models.OneToOneField(
        'Student',
        on_delete=models.CASCADE,
        related_name="degree_audit"
    )

    credits_completed = models.PositiveIntegerField(default=0)
    credits_remaining = models.PositiveIntegerField(default=0)

    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.ON_TRACK
    )

    last_reviewed = models.DateTimeField(auto_now=True)

    def recompute(self):
        """
        Sums already-frozen Enrollment outcomes. No live Course lookups
        here at all — a GradingBand or pass_mark change made today has
        zero effect on enrollments graded in the past, because their
        credits_earned/grade_points_earned were fixed at finalize_grade()
        time, not recalculated now.
        """
        graded = self.student.enrollment_records.filter(
            graded_at__isnull=False)

        credits_completed = graded.aggregate(
            total=models.Sum('credits_earned')
        )['total'] or 0

        graded_and_passed = graded.filter(is_passed=True)
        weighted = sum(
            (e.grade_points_earned or 0) * e.credits_earned
            for e in graded_and_passed
        )
        graded_credits = graded_and_passed.aggregate(
            total=models.Sum('credits_earned')
        )['total'] or 0

        programme = self.student.class_entered.programme
        required = programme.total_credits_required

        self.credits_completed = credits_completed
        self.credits_remaining = max(required - credits_completed, 0)
        if graded_credits:
            self.gpa = round(weighted / graded_credits, 2)

        was_eligible = self.result == self.Result.ELIGIBLE
        newly_eligible = credits_completed >= required

        if newly_eligible:
            self.result = self.Result.ELIGIBLE
        elif self.result != self.Result.ELIGIBLE:
            self.result = self.Result.ON_TRACK
        # else: already eligible but credits dropped below required after
        # the fact (e.g. a regrade) — left alone deliberately. A human
        # decides whether to walk back a nomination.

        self.save()

        if newly_eligible and not was_eligible:
            self._nominate_for_graduation()

    def _nominate_for_graduation(self):
        graduation, created = Graduation.objects.get_or_create(
            student=self.student,
            defaults={
                'Tclass': self.student.class_entered,
                'status': 'nominated',
                'nominated_at': timezone.now(),
                # final_classification is required on the model with no
                # default — left blank here on purpose. Nothing computes
                # First Class/Upper/Lower/Pass from gpa yet, so this is
                # deliberately punted to whoever verifies the nomination.
                'final_classification': '',
            },
        )
        if not created and graduation.status == 'nominated':
            graduation.nominated_at = timezone.now()
            graduation.save(update_fields=['nominated_at'])


class Graduation(BaseModelMixin):
    """
    Data register mapped directly to CUE's graduation data return specifications.
    Tracks academic award distributions across cohorts.
    """

    graduation_status = [
        ("nominated", "Nominated"),
        ("verified", "Verified"),
        ("approved", "Approved"),
        ("conferred", "Conferred")
    ]

    student = models.OneToOneField(
        'Student',
        on_delete=models.PROTECT,
        related_name="graduation_candidacy"
    )

    Tclass = models.ForeignKey(
        "TClass",
        on_delete=models.PROTECT,
        related_name="graduation_candidates"
    )  # graduated with class of

    status = models.CharField(
        max_length=20,
        choices=graduation_status,
        default='nominated'
    )

    final_classification = models.CharField(
        max_length=30,
        choices=CLASSIFICATION_CHOICES,
        help_text="Official degree classification mapped to CUE data guidelines."
    )

    with_honours = models.BooleanField(
        default=True,
        help_text="Flag indicating if the degree was conferred with an Honours distinction."
    )

    thesis_title = models.TextField(
        blank=True,
        null=True,
        help_text="Compulsory for Postgraduate (Masters/PhD) returns"
    )

    nominated_at = models.DateTimeField(null=True, blank=True)

    verified_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_graduations'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_graduations'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Graduation Record"
        verbose_name_plural = "Graduation Records"

    def clean(self):
        """
        CUE Verification Rule: Postgraduates must have a thesis title registered,
        and Doctorates do not carry standard Honours flags.
        """
        super().clean()

        # Guardrail: Check if the student belongs to a Postgraduate track via their program layout

        # TODO :  replace to check class if it is a phd class
        if hasattr(self.student, 'enrolments'):
            latest_enrolment = self.student.enrolments.order_with_respect_to(
                'year_of_study'
            ).last()
            if latest_enrolment and latest_enrolment.program.program_code.upper().startswith(('MSC', 'PHD', 'MA')):

                # Check 1: Mandatory thesis titles for higher degrees
                if not self.thesis_title:
                    raise ValidationError({
                        'thesis_title': "CUE quality data returns require a verified Thesis/Dissertation title for all Postgraduate awards."
                    })

                # Check 2: Adjust Honours logic for Doctorates if accidentally checked true
                if latest_enrolment.program.program_code.upper().startswith('PHD') and self.with_honours:
                    raise ValidationError({
                        'with_honours': "Doctoral/PhD programs are not awarded with Honours designations under standard guidelines."
                    })

    def verify(self, by_user, classification=None):
        """HOD/Dean step: confirms the nomination is legitimate."""
        if self.status != 'nominated':
            raise ValidationError(
                f"Cannot verify a graduation candidacy in status '{self.status}' — "
                f"only a 'nominated' candidacy can be verified."
            )
        if classification:
            self.final_classification = classification
        elif not self.final_classification:
            raise ValidationError(
                "final_classification must be set at verification — either pass "
                "one in here or set it on the record before calling verify()."
            )
        self.status = 'verified'
        self.verified_by = by_user
        self.verified_at = timezone.now()
        self.save()

    def approve(self, by_user):
        """Registrar step: final sign-off before conferral."""
        if self.status != 'verified':
            raise ValidationError(
                f"Cannot approve a graduation candidacy in status '{self.status}' — "
                f"it must be 'verified' first."
            )
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Graduated: {self.student.registration_number} ({self.Tclass}) - {self.get_final_classification_display()} - {self.status}"


class Diploma(BaseModelMixin):
    candidacy = models.OneToOneField(
        'Graduation',
        on_delete=models.CASCADE,
        related_name="diploma"
    )
    diploma_number = models.CharField(max_length=50, unique=True)
    conferred_date = models.DateField()
    issued = models.BooleanField(default=False)
    file = models.FileField(
        upload_to="registrar/diplomas/",
        blank=True,
        null=True
    )


class Convocation(BaseModelMixin):
    name = models.CharField(max_length=150)  # e.g. "42nd Convocation"
    date = models.DateField()
    venue = models.CharField(
        max_length=255,
        blank=True
    )
    candidates = models.ManyToManyField(
        'Graduation',
        related_name="convocations",
        blank=True
    )
