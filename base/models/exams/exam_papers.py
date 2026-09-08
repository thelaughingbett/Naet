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
Exam papers & question bank domain — setting and moderating the paper
that will be sat for an ExamSession, and the reusable pool of
questions courses can draw papers from.

Distinct from the attendance/results modules: this is all pre-exam
content workflow (draft -> submitted -> moderated -> approved/rejected),
not what happened during or after the sitting.
"""

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


class QuestionPaper(BaseModelMixin):

    paper_Status = [
        ("draft", "Draft"),
        ("submitted", "Submitted for Moderation"),
        ("moderated", "Moderated"),
        ("approved", "Approved"),
        ("rejected", "Rejected")
    ]

    exam = models.OneToOneField(
        "ExamSession",
        on_delete=models.CASCADE,
        related_name="question_paper"
    )

    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name="question_papers_set"
    )

    file = models.FileField(
        upload_to="exams/question_papers/"
    )

    version = models.PositiveSmallIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=paper_Status,
        default='draft'
    )


class QuestionPaperModeration(BaseModelMixin):
    question_paper = models.ForeignKey(
        'QuestionPaper',
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
        "Course",
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
