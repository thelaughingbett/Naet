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

from django.db import modelss


from django.conf import settings


class Application(BaseModelMixin):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        DOCS_PENDING = "docs_pending", "Documents Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        ENROLLED = "enrolled", "Enrolled"

    applicant_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    program_applied = models.ForeignKey(
        'Programme',
        on_delete=models.CASCADE,
        related_name="applications"
    )
    term_applied = models.ForeignKey(
        'Session',
        on_delete=models.CASCADE,
        related_name="applications"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    submitted_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications_reviewed"
    )

    def __str__(self):
        return f"{self.applicant_name} -> {self.program_applied}"


class ApplicationDocument(BaseModelMixin):
    class DocType(models.TextChoices):
        TRANSCRIPT = "transcript", "Prior Transcript"
        ID_PROOF = "id_proof", "ID Proof"
        RECOMMENDATION = "recommendation", "Recommendation Letter"
        ESSAY = "essay", "Personal Statement"
        OTHER = "other", "Other"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file = models.FileField(upload_to="admissions/documents/")
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="documents_verified"
    )


class TransferCreditEvaluation(BaseModelMixin):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="transfer_credits"
    )
    external_course_name = models.CharField(max_length=255)
    external_institution = models.CharField(max_length=255)
    equivalent_course = models.ForeignKey(
        'Course',
        on_delete=models.SET_NULL,
        null=True, blank=True
        # should an api for external students to request transfers and have access to course catalog [can base on unesco or cue codes]
    )
    credits_awarded = models.PositiveSmallIntegerField(default=0)
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    approved = models.BooleanField(default=False)
