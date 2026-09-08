# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


class StatusChangeRequest(BaseModelMixin):
    class ChangeType(models.TextChoices):
        LEAVE_OF_ABSENCE = "leave", "Leave of Absence"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        READMISSION = "readmission", "Readmission"
        PROGRAM_TRANSFER = "program_transfer", "Program Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="status_change_requests"
    )
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices
    )
    reason = models.TextField(blank=True)
    supporting_document = models.FileField(
        upload_to="registrar/status_changes/",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes_processed"
    )
    effective_date = models.DateField(null=True, blank=True)
