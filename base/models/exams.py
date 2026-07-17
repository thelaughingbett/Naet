# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import BaseModelMixin
from django.db import models


from base.models import (
    ExamSession,
    Course,
    Student,
    Session,
    Result
)

from django.db import modelss


from django.conf import settings


class QuestionPaper(BaseModelMixin):

    paper_Status = [
        ("draft", "Draft"),
        ("submitted", "Submitted for Moderation"),
        ("moderated", "Moderated"),
        ("approved", "Approved"),
        ("rejected", "Rejected")
    ]

    exam = models.OneToOneField(
        ExamSession,
        on_delete=models.CASCADE,
        related_name="question_paper"
    )

    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name="question_papers_set"
    )

    file = models.FileField(upload_to="exams/question_papers/")

    version = models.PositiveSmallIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=paper_Status,
        default='draft'
    )


class QuestionPaperModeration(BaseModelMixin):
    question_paper = models.ForeignKey(
        QuestionPaper,
        on_delete=models.CASCADE,
        related_name="moderations"
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    comments = models.TextField(blank=True)
    approved = models.BooleanField(default=False)


class QuestionBankItem(BaseModelMixin):
  # INGORE  for lms ?
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="question_bank_items"
    )

    question_text = models.TextField()

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM
    )

    marks = models.PositiveSmallIntegerField(default=5)

    topic = models.CharField(max_length=150, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True
    )


# ---------------------------------------------------------------------------
# EXAM DEPARTMENT: Hall tickets & attendance
# ---------------------------------------------------------------------------


class ExamAttendance(BaseModelMixin):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        MALPRACTICE = "malpractice", "Malpractice Reported"

    exam_session = models.OneToOneField(
        ExamSession,
        on_delete=models.CASCADE,
        related_name="attendance"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABSENT
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    remarks = models.TextField(blank=True)


# ---------------------------------------------------------------------------
# EXAM DEPARTMENT: Results & grading
# ---------------------------------------------------------------------------

class GradeScale(BaseModelMixin):
    """Configurable letter-grade boundaries, e.g. A: 80-100."""

    grade = models.CharField(max_length=5)  # A, A-, B+, ...
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        ordering = ["-min_percentage"]

    def __str__(self):
        return self.grade


# class Result(BaseModelMixin):
#     class Status(models.TextChoices):
#         PENDING = "pending", "Pending Entry"
#         ENTERED = "entered", "Entered"
#         PUBLISHED = "published", "Published"
#         WITHHELD = "withheld", "Withheld"

#     hall_ticket = models.OneToOneField(
#         HallTicket, on_delete=models.CASCADE, related_name="result")
#     marks_obtained = models.DecimalField(
#         max_digits=6, decimal_places=2, null=True, blank=True)
#     grade = models.ForeignKey(
#         GradeScale, on_delete=models.SET_NULL, null=True, blank=True, related_name="results")
#     status = models.CharField(
#         max_length=20, choices=Status.choices, default=Status.PENDING)
#     entered_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="results_entered"
#     )
#     published_on = models.DateTimeField(null=True, blank=True)


class GradeCard(BaseModelMixin):
    """Consolidated term result summary for a student."""
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="grade_cards")
    term = models.ForeignKey(
        Session,
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
        Result,
        on_delete=models.CASCADE,
        related_name="revaluation_requests"
    )
    student = models.ForeignKey(
        Student,
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
        Student,
        on_delete=models.CASCADE,
        related_name="backlog_registrations"
    )
    original_result = models.ForeignKey(
        Result,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backlog_attempts"
    )
    exam = models.ForeignKey(
        ExamSession,
        on_delete=models.CASCADE,
        related_name="backlog_registrations"
    )
    attempt_number = models.PositiveSmallIntegerField(default=2)
    fee_paid = models.BooleanField(default=False)


class TranscriptRequest(BaseModelMixin):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        ISSUED = "issued", "Issued"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="transcript_requests"
    )
    purpose = models.CharField(max_length=255, blank=True)
    delivery_method = models.CharField(
        max_length=50,
        default="digital"
    )  # digital, mail, pickup -> make enum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )
    issued_file = models.FileField(
        upload_to="registrar/transcripts/",
        blank=True,
        null=True
    )
    requested_on = models.DateTimeField(auto_now_add=True)
    fee_paid = models.BooleanField(default=False)


class Certificate(BaseModelMixin):
    class CertType(models.TextChoices):
        BONAFIDE = "bonafide", "Bonafide Certificate"
        PROVISIONAL = "provisional", "Provisional Degree Certificate"
        DEGREE_VERIFICATION = "degree_verification", "Degree Verification"
        CONDUCT = "conduct", "Conduct Certificate"

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="certificates"
    )
    cert_type = models.CharField(max_length=30, choices=CertType.choices)
    issued_on = models.DateField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    file = models.FileField(
        upload_to="registrar/certificates/",
        blank=True,
        null=True
    )
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )
