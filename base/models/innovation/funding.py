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


class GrantScheme(BaseModelMixin):
    name = models.CharField(max_length=255)
    # e.g. govt body, internal fund
    funding_agency = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    max_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )
    application_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GrantApplication(BaseModelMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    scheme = models.ForeignKey(
        'GrantScheme',
        on_delete=models.CASCADE,
        related_name="applications"
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grant_applications"
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grant_applications"
    )
    amount_requested = models.DecimalField(max_digits=14, decimal_places=2)
    proposal_document = models.FileField(
        upload_to="grants/proposals/",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    submitted_on = models.DateField(null=True, blank=True)


class SeedFundDisbursement(BaseModelMixin):
    class Tranche(models.TextChoices):
        FIRST = "first", "First Tranche"
        SECOND = "second", "Second Tranche"
        FINAL = "final", "Final Tranche"

    application = models.ForeignKey(
        'GrantApplication',
        on_delete=models.CASCADE,
        related_name="disbursements"
    )
    tranche = models.CharField(max_length=10, choices=Tranche.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    disbursed_on = models.DateField(null=True, blank=True)
    utilization_report = models.FileField(
        upload_to="grants/utilization/",
        blank=True,
        null=True
    )


class Investor(BaseModelMixin):
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True)
    investor_type = models.CharField(
        max_length=100,
        blank=True
    )  # Angel, VC, Corporate
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    focus_sectors = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name
