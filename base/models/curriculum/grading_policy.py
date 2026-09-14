# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Course-level grading configuration: how a score becomes grade points
(GradingScale/GradingBand), and how multiple CAT/Exam/etc. results
combine into one final score for a course (WeightingScheme/
WeightingComponent, with per-component aggregation strategies).

Lives in base/models/curriculum/ rather than base/models/adminstration/
because this is course/curriculum configuration, not a student
lifecycle event — Course.pass_mark, Course.grading_scale, and
Course.weighting_scheme all point back here, and Curriculum
(base/models/curriculum/curriculum.py) can override the weighting
scheme per class-offering via weighting_scheme_override.

Consolidates three earlier standalone sketches into one file:
course-level pass_mark/grading_scale, the weighting scheme + per-course/
per-curriculum resolution, and the best-N/average/sum/latest
aggregation strategy for multiple same-type results (e.g. 3 CATs).
"""

from decimal import Decimal, ROUND_HALF_UP
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from ..base import BaseModelMixin

# Shared across Result (exams.py/evaluations.py — wherever it actually
# lives) and WeightingComponent below, so both can reference the same
# type codes without importing Result into this file.
RESULT_TYPE_CHOICES = [
    ('C', 'Cat'),
    ('E', 'Exams'),
    ('P', 'Practicals'),
    ('A', 'Assignments'),
    ('Q', 'Quizzes'),
    ('PR', 'Projects'),
]

TWO_PLACES = Decimal('0.01')


# --- Grading scale (score -> grade points) ----------------------------

class GradingScale(BaseModelMixin):
    """
    A named set of score->grade-point bands, e.g. "Undergraduate
    standard" (A=70+, B=60-69, ...). Shared across whichever courses
    reference it via Course.grading_scale.
    """
    name = models.CharField(max_length=100, unique=True)

    is_default = models.BooleanField(
        default=False,
        help_text="Used by any Course with grading_scale left blank. "
        "Only one scale should have this set — enforced in clean()."
    )

    def clean(self):
        super().clean()
        if self.is_default:
            clashing = GradingScale.objects.filter(
                is_default=True
            ).exclude(pk=self.pk)
            if clashing.exists():
                raise ValidationError({
                    'is_default': "Another grading scale is already marked default "
                    f"({clashing.first().name}). Unset it before making this one default."
                })

    def grade_points_for(self, score):
        """
        Highest band whose min_score <= score. Raises if no band covers
        this score — a scale missing a min_score=0 floor band is a
        data-integrity problem worth surfacing loudly.
        """
        band = self.bands.filter(
            min_score__lte=score).order_by('-min_score').first()
        if band is None:
            raise ValidationError(
                f"Grading scale '{self.name}' has no band covering a score of {score} "
                f"— it needs a band with min_score=0 as a floor."
            )
        return band.grade_points

    def __str__(self):
        return self.name


class GradingBand(BaseModelMixin):
    scale = models.ForeignKey(
        GradingScale, on_delete=models.CASCADE, related_name='bands'
    )
    min_score = models.PositiveIntegerField(
        help_text="Lowest score (inclusive) that earns this band's grade points."
    )
    grade_points = models.DecimalField(max_digits=3, decimal_places=2)
    label = models.CharField(
        max_length=5, blank=True, help_text="e.g. 'A', 'B+' — display only."
    )

    class Meta:
        unique_together = ('scale', 'min_score')
        ordering = ['-min_score']

    def __str__(self):
        return f"{self.scale.name}: {self.min_score}+ -> {self.grade_points} ({self.label})"


# --- Weighting scheme (how CAT/Exam/etc. combine into one score) -----

class WeightingScheme(BaseModelMixin):
    """A named set of result-type weights, e.g. 'Standard 30/70' =
    {CAT: 30%, Exam: 70%}. Resolved per Course by default, overridable
    per Curriculum (a specific lecturer's specific class offering)."""

    name = models.CharField(max_length=100, unique=True)

    is_default = models.BooleanField(
        default=False,
        help_text="Institution-wide fallback when neither a Course nor a "
        "specific Curriculum offering specifies its own scheme."
    )

    def clean(self):
        super().clean()
        if self.is_default:
            clashing = WeightingScheme.objects.filter(
                is_default=True
            ).exclude(pk=self.pk)
            if clashing.exists():
                raise ValidationError({
                    'is_default': "Another weighting scheme is already default "
                    f"({clashing.first().name}). Unset it first."
                })

    def total_weight(self):
        return self.components.aggregate(
            total=models.Sum('weight_percent')
        )['total'] or Decimal('0')

    def validate_weights_sum_to_100(self):
        """
        Not enforced automatically on save() — components are added one
        row at a time, so blocking mid-entry saves at != 100% would be
        wrong. Call this explicitly before treating a scheme as usable
        (a seed command, an admin action, or before assigning it live).
        """
        total = self.total_weight()
        if total != Decimal('100'):
            raise ValidationError(
                f"Weighting scheme '{self.name}' has components summing to "
                f"{total}%, not 100%. Fix before using it to grade anything."
            )

    def __str__(self):
        parts = ", ".join(
            f"{c.get_result_type_display()} {c.weight_percent}%"
            for c in self.components.all()
        )
        return f"{self.name} ({parts})" if parts else self.name


class WeightingComponent(BaseModelMixin):
    """
    One weighted piece of a WeightingScheme, e.g. "CAT counts 30%".
    Also owns HOW multiple results of that same type combine into this
    component's single contributed score (aggregation).
    """

    class Aggregation(models.TextChoices):
        AVERAGE_ALL = "average_all", "Average all submissions"
        BEST_N = "best_n", "Average the best N submissions"
        SUM = "sum", "Sum all submissions"
        LATEST = "latest", "Most recent submission only"

    scheme = models.ForeignKey(
        WeightingScheme, on_delete=models.CASCADE, related_name='components'
    )
    result_type = models.CharField(max_length=2, choices=RESULT_TYPE_CHOICES)
    weight_percent = models.DecimalField(max_digits=5, decimal_places=2)

    aggregation = models.CharField(
        max_length=15, choices=Aggregation.choices, default=Aggregation.AVERAGE_ALL,
        help_text="How multiple results of this type combine into this "
        "component's score. e.g. three CATs: average all three, "
        "or drop the worst and average the best 2."
    )
    expected_count = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="How many results of this type the lecturer plans to "
        "give (e.g. 3 CATs). REQUIRED for 'best_n' — without "
        "knowing the total, the system can't tell 'still waiting "
        "on more CATs' apart from 'that's all of them.' Optional "
        "for the other strategies; leave blank if any number of "
        "submissions should count as complete."
    )
    best_n_count = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Only used when aggregation='best_n' — how many of the "
        "top scores to average, e.g. 2 (best 2 of 3)."
    )

    class Meta:
        unique_together = ('scheme', 'result_type')

    def clean(self):
        super().clean()
        if self.aggregation == self.Aggregation.BEST_N:
            if not self.best_n_count:
                raise ValidationError({
                    'best_n_count': "best_n aggregation requires best_n_count "
                    "(e.g. 2, for 'best 2 of N')."
                })
            if not self.expected_count:
                raise ValidationError({
                    'expected_count': "best_n aggregation requires expected_count "
                    "so the system knows when all submissions are in."
                })
            if self.best_n_count > self.expected_count:
                raise ValidationError({
                    'best_n_count': f"best_n_count ({self.best_n_count}) can't exceed "
                    f"expected_count ({self.expected_count})."
                })

    def compute(self, results_qs):
        """
        results_qs: published Result rows of this component's result_type
        for one enrollment, in submission order.

        Returns the aggregated score, or None if not enough results have
        been submitted yet to consider this component complete.
        """
        scores = list(results_qs.order_by(
            'record_id').values_list('score', flat=True))
        count = len(scores)

        if count == 0:
            return None
        if self.expected_count and count < self.expected_count:
            return None  # still waiting on more submissions of this type

        if self.aggregation == self.Aggregation.AVERAGE_ALL:
            return (sum(scores) / count).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        if self.aggregation == self.Aggregation.SUM:
            return sum(scores)

        if self.aggregation == self.Aggregation.LATEST:
            return scores[-1]

        if self.aggregation == self.Aggregation.BEST_N:
            best = sorted(scores, reverse=True)[:self.best_n_count]
            return (sum(best) / len(best)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        raise ValidationError(
            f"Unknown aggregation strategy '{self.aggregation}'.")

    def __str__(self):
        return (f"{self.scheme.name}: {self.get_result_type_display()} "
                f"= {self.weight_percent}% ({self.get_aggregation_display()})")
