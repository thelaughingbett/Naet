# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Academic records administration domain — the exam department's
downstream processing of already-published results: consolidating
them into a term's GradeCard, handling a student's dispute over one
(RevaluationRequest), and re-sitting a failed course
(BacklogRegistration).

Distinct from `enrollment.py`'s Enrollment/Result: those own the raw
per-assessment scores and the frozen pass/fail outcome for a single
course. This module sits one layer above — it reacts to those
outcomes (an SGPA/CGPA rollup across a whole term, a request to
re-mark one already-published Result, a fresh attempt registered
against a past failing Result) rather than producing them.
"""

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


class GradeCard(BaseModelMixin):
    """Consolidated term result summary for a student."""
    student = models.ForeignKey(
        "Student", on_delete=models.CASCADE, related_name="grade_cards")
    term = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="grade_cards"
    )

    sgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    file = models.FileField(
        upload_to="exams/grade_cards/",
        blank=True,
        null=True
    )

    generated_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "term")


class RevaluationRequest(BaseModelMixin):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        UNDER_REVIEW = "under_review", "Under Review"
        MARKS_CHANGED = "marks_changed", "Marks Changed"
        MARKS_UNCHANGED = "marks_unchanged", "Marks Unchanged"

    result = models.ForeignKey(
        "Result",
        on_delete=models.CASCADE,
        related_name="revaluation_requests"
    )
    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="revaluation_requests"
    )
    reason = models.TextField(blank=True)
    fee_paid = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )
    revised_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


class BacklogRegistration(BaseModelMixin):
    """Supplementary/backlog exam registration for a previously failed course."""

    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="backlog_registrations"
    )

    original_result = models.ForeignKey(
        "Result",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backlog_attempts"
    )

    exam = models.ForeignKey(
        "ExamSession",
        on_delete=models.CASCADE,
        related_name="backlog_registrations"
    )

    attempt_number = models.PositiveSmallIntegerField(default=2)
    fee_paid = models.BooleanField(default=False)
