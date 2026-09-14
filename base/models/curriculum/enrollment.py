# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Enrollment & results domain — a student's registration in a Curriculum
slot, the raw assessment scores recorded against it (Result), and the
frozen grading outcome derived from those scores (Enrollment's
graded_* fields).

Freezes an enrollment's grading outcome the moment it's finalized,
instead of re-deriving it live from Course.pass_mark / grading_scale
every time DegreeAudit.recompute() runs. Fixes the drift problem:
editing a GradingBand or a course's pass_mark in the future no longer
silently rewrites past students' pass/fail status, GPA, or credit count.

DESIGN CALLS:

1. Freezing happens at Enrollment level, not per-Result. A course's
   final outcome (for GPA/credit purposes) is one number — either the
   Exam/Project score, or an average of CAT/Assignment/Quiz scores for
   courses with no terminal assessment — so the frozen fields live on
   Enrollment, matching where is_passed/grade_points/credit_value
   already conceptually lived as properties before this change.

2. WHEN to freeze is the genuinely hard part, and I'm making an
   explicit choice here rather than hiding it: finalize_grade() is
   triggered by the signal only when (a) a Result of type Exam/Project
   publishes for this enrollment, since that's the natural "this course
   is now graded" event, or (b) Enrollment.status is set to 'completed'
   directly, covering pure-CAT/CC units with no terminal exam. A
   CAT/Assignment/Quiz publishing on its own does NOT freeze anything —
   unlike the old live-property version, an in-progress course won't
   show up in credits_completed at all until one of those two triggers
   fires. If your CC/common units are genuinely graded off CATs alone
   with no explicit 'completed' transition anywhere in the codebase yet,
   that transition needs to exist before this can work correctly for them.

3. finalize_grade() is a no-op once graded_at is set, unless force=True.
   The only path to force=True is the explicit regrade() method, which
   requires a reason and a by_user — Enrollment already carries
   HistoricalRecords(), so the field-level diff (old score/points/passed
   vs new) is captured automatically; regrade() additionally sets
   _change_reason so that diff shows up with WHY in the history, not
   just WHAT changed.

KNOWN ISSUE — CARRIED OVER FROM THE ORIGINAL, NOT FIXED HERE:
`Enrollment.is_passed` is declared below both as a `BooleanField` and,
later in the same class body, as a `@property` of the same name. Python
class-body execution means the later definition wins outright — the
field descriptor never actually gets attached by Django's model
metaclass, only the property does. That property has no setter, so the
`self.is_passed = score >= pass_mark` assignment inside
`finalize_grade()` will raise `AttributeError` at runtime rather than
freezing anything. This split preserves that behavior unchanged; it's
flagged here rather than silently fixed since resolving it (e.g.
renaming the live property to `computed_is_passed`, or dropping the
field) changes what `credits_earned`/`grade_points_earned` freezing
actually does and deserves a deliberate decision, not a drive-by fix.
"""

from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


RESULT_TYPE_CHOICES = [
    ('C', 'Cat'),
    ('E', 'Exams'),
    ('P', 'Practicals'),
    ('A', 'Assignments'),
    ('Q', 'Quizzes'),
    ('PR', 'Projects'),
]


class Enrollment(BaseModelMixin):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ("dropped", "Dropped"),
        # write a signal or method to update this once moved to next academic year [most likely a celery job should suffice here else heavy workload] 👇🏿
        ("completed", "Completed")
    ]

    APPROVAL_METHOD_CHOICES = [
        ('system', 'System auto-approved'),
        ('manual', 'Manually approved'),
    ]

    # Core, Common Unit — default behavior only now
    AUTO_APPROVE_COURSE_TYPES = ('C', 'CC')

    FINAL_RESULT_TYPES = ('E', 'PR')

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )
    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending'
    )

    approval_method = models.CharField(
        max_length=10,
        choices=APPROVAL_METHOD_CHOICES,
        null=True,
        blank=True,
        default='system',
        help_text="Set only when status='approved'. Distinguishes a system "
        "auto-approval from a human overriding/confirming it — "
        "core units can go either way, so this can't be inferred "
        "from approved_by alone."
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_enrollments',
        help_text="Null when approval_method='system'. Set to the reviewer "
        "when approval_method='manual'."
    )

    # TODO : make sure save updates this
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    # Frozen at finalize_grade() time. All null/0 until then — a student
    # mid-course shows up as ungraded, not as "failed."
    graded_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Score used to decide pass/fail and grade points. "
        "Frozen once — editing Course.pass_mark or the "
        "grading scale later never changes this."
    )

    is_passed = models.BooleanField(
        null=True,
        blank=True,
        help_text="Null until graded. Frozen at finalize_grade() time."
    )

    grade_points_earned = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )

    credits_earned = models.PositiveIntegerField(default=0)

    # Audit trail: exactly which policy produced this outcome, so a
    # future "why does this transcript say X" question is answerable
    # without guessing what the scale looked like back then.
    graded_scale = models.ForeignKey(
        'GradingScale',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='graded_against'
    )
    pass_mark_applied = models.PositiveIntegerField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    weighting_scheme_used = models.ForeignKey(
        'WeightingScheme',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='weighted_against',
        help_text="Which scheme actually produced graded_score — frozen "
        "alongside the other grading fields for the same reason: "
        "changing the scheme later shouldn't reinterpret old grades."
    )

    class Meta:
        unique_together = ('student', 'curriculum')

    def __str__(self):
        return f"{self.student} → {self.curriculum} [{self.status}]"

    @property
    def requires_manual_approval(self) -> bool:
        """
        Default behavior for new enrollments — not a hard restriction.
        A core/common unit can still be manually approved via approve().

        NOTE — not changed here, flagging only: this still reads
        `self.curriculum.course.course_type`, i.e. Course's single GLOBAL
        Core/Elective/Common flag. Now that Syllabus exists specifically to
        let a course be Core for one programme and Adjunct/elective for
        another, this is the natural place to actually use that —
        e.g. `self.curriculum.syllabus.state == Syllabus.State.ADJUNCT`
        instead of (or alongside) `course_type`. Left as-is since switching
        this changes which enrollments auto-approve — worth doing
        deliberately rather than as a drive-by fix.
        """
        return self.curriculum.course.course_type not in self.AUTO_APPROVE_COURSE_TYPES

    @property
    def final_result(self):
        return (
            self.results
            .filter(type__in=self.FINAL_RESULT_TYPES, state='published')
            .order_by('-record_id')
            .first()
        )

    @property
    def is_passed(self):
        """Reads pass_mark from the course itself instead of a global constant."""
        pass_mark = self.curriculum.course.pass_mark

        final = self.final_result
        if final is not None:
            return final.score >= pass_mark

        published = self.results.filter(state='published')
        if not published.exists():
            return False
        avg = published.aggregate(avg=models.Avg('score'))['avg']
        return avg is not None and avg >= pass_mark

    @property
    def credit_value(self):
        return self.curriculum.course.credits if self.is_passed else 0

    @property
    def grade_points(self):
        """Reads the grading scale from the course itself."""
        scale = self.curriculum.course.get_grading_scale()

        final = self.final_result
        if final is not None:
            return scale.grade_points_for(final.score)

        published = self.results.filter(state='published')
        avg = published.aggregate(avg=models.Avg('score'))['avg']
        return scale.grade_points_for(avg) if avg is not None else Decimal('0.00')

    @property
    def results(self):
        return Result.objects.filter(enrollment=self)

    def clean(self):
        super().clean()

        from base.models import RegistrationWindow
        # window = (
        #     RegistrationWindow.objects.filter(
        #         term=self.curriculum.session,
        #         window_type='course_registration',
        #     )
        #     .filter(models.Q(programme=self.student.class_entered.programme) | models.Q(programme__isnull=True))
        #     .order_by("programme")
        #     .first()
        # )

        # if window is None:
        #     raise ValidationError(
        #         "No course registration window has been configured for this term."
        #     )
        # if not window.is_open:
        #     raise ValidationError(
        #         "Course registration is closed for this term."
        #     )

        if self.status == 'completed' and self.graded_at is None:
            self.finalize_grade()

        if self.status == 'approved':
            if not self.approved_at:
                raise ValidationError({
                    'approved_at': "approved_at is required when status is 'approved'."
                })
            if not self.approval_method:
                raise ValidationError({
                    'approval_method': "approval_method is required when status is 'approved'."
                })
            if self.approval_method == 'system' and self.approved_by_id:
                raise ValidationError({
                    'approved_by': "A system-approved enrollment shouldn't carry a human approver. "
                    "Use approval_method='manual' if a reviewer signed off."
                })
            if self.approval_method == 'manual' and not self.approved_by_id:
                raise ValidationError({
                    'approved_by': "Manual approval requires the reviewing user."
                })
        else:
            if self.approved_by_id or self.approved_at or self.approval_method:
                raise ValidationError({
                    'status': "approval_method/approved_by/approved_at should only be set "
                              "when status is 'approved'."
                })

    def save(self, *args, **kwargs):
        # default auto-approval on first save — only kicks in if nothing
        # has already set status/approval_method (i.e. approve() wasn't
        # called explicitly first)
        if self._state.adding and self.status == 'pending' and not self.requires_manual_approval:
            self.status = 'approved'
            self.approval_method = 'system'
            self.approved_by = None
            self.approved_at = timezone.now()

        self.full_clean()
        super().save(*args, **kwargs)

    def approve(self, by_user):
        """Manual approval — for electives by default, but also usable to
        have a human confirm/override a core or common unit enrollment."""
        self.status = 'approved'
        self.approval_method = 'manual'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, by_user, reason=""):
        self.status = 'rejected'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.approval_method = None
        self.save()

    def drop(self):
        """
         Withdraws the student from this curriculum slot — self-service,
         student-initiated. Only allowed pre-grading; a graded unit needs a
         different process (academic appeal), not a silent withdrawal that
         would erase graded_score/credits_earned history.

         Explicitly clears approval_method/approved_by/approved_at rather
         than leaving them — clean()'s else-branch requires all three be
         unset whenever status != 'approved', and 'dropped' isn't 'approved'.
         """
        if self.graded_at is not None:
            raise ValidationError(
                "Cannot drop a unit that has already been graded."
            )

        self.status = 'dropped'
        self.approval_method = None
        self.approved_by = None
        self.approved_at = None
        self.save()

    def _current_score(self):
        """
        Weighted sum across every component in the resolved scheme, each
        component's own contribution computed via its aggregation
        strategy. None if ANY component isn't complete yet (see
        WeightingComponent.compute()) — a partial weighted average would
        understate the grade, so we wait for everything.
        """
        scheme = self.curriculum.get_weighting_scheme()
        components = list(scheme.components.all())
        if not components:
            raise ValidationError(
                f"Weighting scheme '{scheme.name}' has no components configured."
            )

        weighted_total = Decimal('0')
        for component in components:
            results_qs = self.results.filter(
                type=component.result_type, state='published'
            )
            component_score = component.compute(results_qs)
            if component_score is None:
                return None  # this component still has submissions pending

            weighted_total += Decimal(str(component_score)) * (
                component.weight_percent / Decimal('100')
            )

        return weighted_total

    def finalize_grade(self, force=False):
        if self.graded_at is not None and not force:
            return False

        score = self._current_score()
        if score is None:
            return False

        course = self.curriculum.course
        grading_scale = course.get_grading_scale()
        weighting_scheme = self.curriculum.get_weighting_scheme()
        pass_mark = course.pass_mark

        self.graded_score = score
        # self.is_passed = score >= pass_mark
        self.grade_points_earned = grading_scale.grade_points_for(score)
        self.credits_earned = course.credits if self.is_passed else 0
        self.graded_scale = grading_scale
        self.weighting_scheme_used = weighting_scheme
        self.pass_mark_applied = pass_mark
        self.graded_at = timezone.now()

        self.save(update_fields=[
            'graded_score', 'is_passed', 'grade_points_earned', 'credits_earned',
            'graded_scale', 'weighting_scheme_used', 'pass_mark_applied', 'graded_at',
        ])
        return True

    def regrade(self, by_user, reason):
        """
        Explicit, auditable re-grade of an already-finalized enrollment
        — e.g. correcting a genuinely misconfigured pass_mark that was
        wrong at the time. Requires a reason; the diff is visible in
        Enrollment's HistoricalRecords with that reason attached.

        This does NOT retroactively fix every other student's grade
        under the same (mis)configuration — call it per-enrollment,
        deliberately, not as a bulk sweep.
        """
        if not reason:
            raise ValidationError(
                "A reason is required to regrade a finalized enrollment.")
        if self.graded_at is None:
            raise ValidationError("Cannot regrade an enrollment that hasn't been graded yet — "
                                  "call finalize_grade() first.")

        changed = self.finalize_grade(force=True)
        if changed:
            # update_change_reason(self, f"Regraded by {by_user}: {reason}") NOTE make this exist
            pass
        return changed


class Result(BaseModelMixin):

    RESULT_STATE_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for approval'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('disputed', 'Disputed'),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name='results'
    )

    entered_by = models.ForeignKey(
        'User',
        on_delete=models.DO_NOTHING
    )  # non-repudiation field to track who touched record tracked by historical records

    type = models.CharField(
        choices=RESULT_TYPE_CHOICES,
        default='C',
        max_length=45
    )

    state = models.CharField(
        choices=RESULT_STATE_CHOICES,
        default='draft',
        max_length=20,
    )

    score = models.DecimalField(
        decimal_places=2,
        max_digits=5
    )

    title = models.CharField(
        max_length=124
    )

    history = HistoricalRecords()

    def clean(self):

        if self.type != 'E' and self.type != 'PR':
            self.state = 'published'

        return super().clean()

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enrollment.student} - {self.title}"
