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
Registrar documents domain — official paperwork the registrar's office
issues to a student on request (transcripts) or as a matter of record
(certificates). Neither model touches grading logic directly; both
just package up already-settled academic facts into an issuable file.
"""

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


class TranscriptRequest(BaseModelMixin):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        ISSUED = "issued", "Issued"
        REJECTED = "rejected", "Rejected"

    DELIVERY_METHOD_CHOICES = [
        ('digital', "Digital / Portal"),
        ('mail', "Email"),
        ('pickup', "Department pickup / Physically issued")
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="transcript_requests"
    )

    purpose = models.CharField(max_length=255, blank=True)

    delivery_method = models.CharField(
        max_length=50,
        default="digital",
        choices=DELIVERY_METHOD_CHOICES
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
    cert_type = models.CharField(
        max_length=30,
        choices=CertType.choices
    )

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
