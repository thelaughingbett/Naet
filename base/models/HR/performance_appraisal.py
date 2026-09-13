"""
Lecturer Performance Appraisal.

Three-part structure:
  - AppraisalCycle       — the configurable review period (e.g. "2025/2026 Annual Review")
  - PerformanceAppraisal — one lecturer's appraisal within one cycle, with a
                            real self-assessment -> HOD review -> Dean
                            approval workflow (same state-machine shape as
                            LeaveRequest earlier in this project)
  - AppraisalGoal        — SMART goals set in one cycle, evaluated in the next
  - AppraisalDocument    — supporting evidence (certificates, publication copies)

Deliberately pulls real signals where they already exist elsewhere in the
system (LecturerEvaluation for teaching, Publication for research,
AcademicAppointment for service) rather than treating everything as
free-text the reviewer has to remember and re-type.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from ..base import BaseModelMixin, ValidatedFileMixin


class RatingScale(models.TextChoices):
    """Shared across self-rating, HOD rating, and final rating so all three are comparable."""
    OUTSTANDING = "outstanding", "Outstanding"
    EXCEEDS_EXPECTATIONS = "exceeds_expectations", "Exceeds Expectations"
    MEETS_EXPECTATIONS = "meets_expectations", "Meets Expectations"
    NEEDS_IMPROVEMENT = "needs_improvement", "Needs Improvement"
    UNSATISFACTORY = "unsatisfactory", "Unsatisfactory"


RATING_TO_SCORE = {
    RatingScale.OUTSTANDING: Decimal("5"),
    RatingScale.EXCEEDS_EXPECTATIONS: Decimal("4"),
    RatingScale.MEETS_EXPECTATIONS: Decimal("3"),
    RatingScale.NEEDS_IMPROVEMENT: Decimal("2"),
    RatingScale.UNSATISFACTORY: Decimal("1"),
}


class AppraisalCycle(BaseModelMixin):
    """
    The configurable review period every lecturer is appraised within —
    e.g. "2025/2026 Annual Review". Component weights live here (not
    hardcoded) so different schools/years can weight teaching vs. research
    vs. service differently without a code change.
    """

    name = models.CharField(max_length=150)
    academic_year = models.CharField(
        max_length=9,
        help_text='Format: "2025/2026"'
    )
    start_date = models.DateField()
    end_date = models.DateField()

    self_assessment_deadline = models.DateField()
    hod_review_deadline = models.DateField()
    dean_approval_deadline = models.DateField()

    teaching_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.40")
    )
    research_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.30")
    )
    service_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.30")
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("academic_year",)
        ordering = ["-start_date"]

    def clean(self):
        super().clean()
        total = self.teaching_weight + self.research_weight + self.service_weight
        if total != Decimal("1.00"):
            raise ValidationError(
                f"teaching_weight + research_weight + service_weight must sum to 1.00 "
                f"(currently {total})."
            )
        if self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "End date must be after start date."})

    def __str__(self):
        return self.name


class PerformanceAppraisal(BaseModelMixin):
    """
    One lecturer's appraisal within one AppraisalCycle. Status moves through
    a real workflow rather than a single free-standing "complete" flag, so
    it's always clear whose turn it is to act.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SELF_ASSESSMENT_SUBMITTED = "self_submitted", "Self-Assessment Submitted"
        HOD_REVIEWED = "hod_reviewed", "HOD Reviewed"
        DEAN_APPROVED = "dean_approved", "Dean Approved"
        FINALIZED = "finalized", "Finalized"
        DISPUTED = "disputed", "Disputed by Lecturer"

    lecturer = models.ForeignKey(
        "Lecturer",
        on_delete=models.CASCADE,
        related_name="performance_appraisals"
    )
    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.PROTECT,
        related_name="appraisals"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # --- Self-assessment (lecturer-authored) --------------------------------
    self_assessment_summary = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    challenges_faced = models.TextField(blank=True)
    professional_development = models.TextField(
        blank=True,
        help_text="Courses, conferences, certifications completed this cycle"
    )
    goals_for_next_cycle = models.TextField(blank=True)
    self_rating = models.CharField(
        max_length=25,
        choices=RatingScale.choices,
        null=True,
        blank=True
    )
    self_submitted_at = models.DateTimeField(null=True, blank=True)

    # --- Teaching component --------------------------------------------------
    # average_student_rating is a snapshot taken from LecturerEvaluation at
    # review time, not a live query — appraisals shouldn't silently change
    # value if a student submits a late evaluation after the cycle closes.
    average_student_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Snapshot average of LecturerEvaluation.rating for this cycle",
    )
    courses_taught_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )
    teaching_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )

    # --- Research component ---------------------------------------------------
    publications_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )
    research_projects_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )
    research_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )

    # --- Service component --------------------------------------------------------
    administrative_roles_summary = models.TextField(
        blank=True,
        help_text="Committee memberships, AcademicAppointments held, other service"
    )
    service_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )

    # --- HOD review ---------------------------------------------------------------
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appraisals_reviewed",
    )
    reviewer_comments = models.TextField(blank=True)
    reviewer_rating = models.CharField(
        max_length=25,
        choices=RatingScale.choices,
        null=True,
        blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- Dean approval ------------------------------------------------------------
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appraisals_approved",
    )
    final_rating = models.CharField(
        max_length=25,
        choices=RatingScale.choices,
        null=True,
        blank=True
    )
    final_remarks = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    # --- Dispute --------------------------------------------------------------------
    dispute_remarks = models.TextField(blank=True)
    disputed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("lecturer", "cycle")
        ordering = ["-cycle__start_date"]

    def __str__(self):
        return f"{self.lecturer} — {self.cycle} [{self.status}]"

    @property
    def overall_score(self):
        """
        Weighted composite across teaching/research/service, using the
        cycle's configured weights. None until the HOD has actually scored
        all three components — an incomplete review shouldn't produce a
        misleadingly precise-looking number.
        """
        if None in (self.teaching_score, self.research_score, self.service_score):
            return None
        return (
            self.teaching_score * self.cycle.teaching_weight
            + self.research_score * self.cycle.research_weight
            + self.service_score * self.cycle.service_weight
        ).quantize(Decimal("0.01"))

    @property
    def rating_gap(self):
        """
        True if the lecturer's self-rating and the HOD's rating disagree by
        more than one step on the scale — a useful flag for the Dean to
        look at more closely rather than rubber-stamping.
        """
        if not (self.self_rating and self.reviewer_rating):
            return False
        return abs(
            RATING_TO_SCORE[self.self_rating] -
            RATING_TO_SCORE[self.reviewer_rating]
        ) > 1

    def clean(self):
        super().clean()
        if self.status == self.Status.FINALIZED and not self.final_rating:
            raise ValidationError(
                {"final_rating": "A finalized appraisal must have a final rating."})

    # --- workflow transitions, same shape as LeaveRequest earlier in this project ---

    def submit_self_assessment(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError(
                "Self-assessment can only be submitted from Draft status.")
        self.status = self.Status.SELF_ASSESSMENT_SUBMITTED
        self.self_submitted_at = timezone.now()
        self.full_clean()
        self.save()

    def submit_hod_review(self, by_user, rating, comments, teaching_score, research_score, service_score):
        if self.status != self.Status.SELF_ASSESSMENT_SUBMITTED:
            raise ValidationError(
                "HOD can only review after the self-assessment has been submitted.")
        self.reviewed_by = by_user
        self.reviewer_rating = rating
        self.reviewer_comments = comments
        self.teaching_score = teaching_score
        self.research_score = research_score
        self.service_score = service_score
        self.reviewed_at = timezone.now()
        self.status = self.Status.HOD_REVIEWED
        self.full_clean()
        self.save()

    def approve(self, by_user, final_rating, remarks=""):
        if self.status != self.Status.HOD_REVIEWED:
            raise ValidationError(
                "Dean can only approve after the HOD has reviewed.")
        self.approved_by = by_user
        self.final_rating = final_rating
        self.final_remarks = remarks
        self.approved_at = timezone.now()
        self.status = self.Status.FINALIZED
        self.full_clean()
        self.save()

    def dispute(self, remarks):
        if self.status not in (self.Status.HOD_REVIEWED, self.Status.FINALIZED):
            raise ValidationError(
                "Can only dispute a reviewed or finalized appraisal.")
        self.dispute_remarks = remarks
        self.disputed_at = timezone.now()
        self.status = self.Status.DISPUTED
        self.save()


class AppraisalGoal(BaseModelMixin):
    """
    A SMART goal set within one cycle — typically written into
    `goals_for_next_cycle` as prose, then broken out here as trackable rows
    so the *next* cycle's appraisal can check "did they actually do this."
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        ACHIEVED = "achieved", "Achieved"
        PARTIALLY_ACHIEVED = "partially_achieved", "Partially Achieved"
        NOT_ACHIEVED = "not_achieved", "Not Achieved"

    appraisal = models.ForeignKey(
        PerformanceAppraisal,
        on_delete=models.CASCADE,
        related_name="goals"
    )
    description = models.TextField()
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
    outcome_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.description[:50]} [{self.status}]"


class AppraisalDocument(ValidatedFileMixin, BaseModelMixin):
    """Supporting evidence — teaching award certificates, publication copies, training completion letters."""

    appraisal = models.ForeignKey(
        PerformanceAppraisal,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    description = models.CharField(max_length=255, blank=True)

    allowed_mime_types = {
        ".pdf": ["application/pdf"],
        ".doc": ["application/msword"],
        ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        ".png": ["image/png"],
        ".jpg": ["image/jpeg"],
        ".jpeg": ["image/jpeg"],
    }

    def __str__(self):
        return f"Doc for {self.appraisal}: {self.original_name}"
