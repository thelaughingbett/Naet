"""
Persists the output of risk_score.compute_student_risk_score() so the Dean's
action queue is a fast table scan/filter, not a live recomputation across
every enrolled student on every page load. Recompute via a nightly/weekly
batch job (management command or Celery task) using
StudentRiskScore.record_result(), not on request.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from ..base import BaseModelMixin


class StudentRiskScoreQuerySet(models.QuerySet):
    def for_term(self, term):
        return self.filter(term=term)

    def needing_review(self):
        """The Dean's actual action queue: flagged and not yet actioned."""
        return self.filter(needs_review=True, reviewed=False)

    def by_tier(self, tier):
        return self.filter(tier=tier)

    def ordered_for_queue(self):
        """
        Red first, then Amber, then Green — score descending within each
        tier. Plain `-score` alone isn't enough, since a hard-triggered
        Amber case (e.g. an active deferment, score=7.00 from the demo
        data) should still outrank an un-triggered high-scoring Green case.
        """
        tier_priority = models.Case(
            models.When(tier="red", then=0),
            models.When(tier="amber", then=1),
            models.When(tier="green", then=2),
            output_field=models.IntegerField(),
        )
        return self.annotate(_tier_priority=tier_priority).order_by("_tier_priority", "-score")


class StudentRiskScore(BaseModelMixin):
    """
    One row per student per term — the cached, persisted result of
    risk_score.compute_student_risk_score(). Recomputing overwrites the
    scoring fields but never silently clears a Dean's review notes; see
    record_result() for the resurfacing logic.
    """

    class Tier(models.TextChoices):
        GREEN = "green", "Green"
        AMBER = "amber", "Amber"
        RED = "red", "Red"

    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="risk_scores"
    )

    term = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="student_risk_scores"
    )

    # --- scoring output, mirrors RiskScoreResult field-for-field -----------
    score = models.DecimalField(max_digits=5, decimal_places=2)
    tier = models.CharField(max_length=10, choices=Tier.choices)
    primary_risk_factor = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    secondary_risk_factor = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    contributing_factors = models.JSONField(default=dict)
    hard_triggers = models.JSONField(default=list)
    notes = models.JSONField(default=list)
    needs_review = models.BooleanField(default=False)

    # --- Dean-facing review workflow ----------------------------------------
    # TODO this should be a model
    reviewed = models.BooleanField(
        default=False,
        help_text="Dean has looked at this flag and either acted on it or "
        "confirmed no action is needed.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_risk_scores",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(
        blank=True,
        help_text='e.g. "Already on payment plan" or "Medical leave already granted"'
    )

    computed_at = models.DateTimeField(auto_now=True)

    objects = StudentRiskScoreQuerySet.as_manager()

    class Meta:
        unique_together = ("student", "term")
        ordering = ["-score"]

    def __str__(self):
        return f"{self.student} — {self.term} [{self.tier}, {self.score}]"

    def mark_reviewed(self, by_user, remarks=""):
        self.reviewed = True
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.review_remarks = remarks
        self.save(update_fields=[
                  "reviewed", "reviewed_by", "reviewed_at", "review_remarks"])

    @classmethod
    def record_result(cls, student, term, result):
        """
        Upsert a RiskScoreResult (from risk_score.compute_student_risk_score())
        into storage. If the student was already marked `reviewed` and the
        situation has since gotten worse — tier escalated, or a new hard
        trigger appeared that wasn't there before — automatically flips
        `reviewed` back to False so it resurfaces in the queue. A dismissal
        made against last month's facts shouldn't silently suppress this
        month's worse ones.
        """
        existing = cls.objects.filter(student=student, term=term).first()

        should_resurface = False
        if existing and existing.reviewed:
            tier_rank = {"green": 0, "amber": 1, "red": 2}
            tier_worsened = tier_rank.get(
                result.tier, 0) > tier_rank.get(existing.tier, 0)
            new_hard_triggers = set(result.hard_triggers) - \
                set(existing.hard_triggers)
            should_resurface = tier_worsened or bool(new_hard_triggers)

        obj, _created = cls.objects.update_or_create(
            student=student,
            term=term,
            defaults=dict(
                score=result.score,
                tier=result.tier,
                primary_risk_factor=result.primary_risk_factor,
                secondary_risk_factor=result.secondary_risk_factor,
                contributing_factors=result.contributing_factors,
                hard_triggers=result.hard_triggers,
                notes=result.notes,
                needs_review=result.needs_review,
            ),
        )

        if should_resurface:
            obj.reviewed = False
            obj.reviewed_by = None
            obj.reviewed_at = None
            obj.review_remarks = (
                obj.review_remarks
                + f"\n[Auto-resurfaced {timezone.now():%Y-%m-%d}: situation worsened since last review]"
            ).strip()
            obj.save(update_fields=[
                     "reviewed", "reviewed_by", "reviewed_at", "review_remarks"])

        return obj
