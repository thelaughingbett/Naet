# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Accreditation domain — institutional/programme accreditation status
with an external regulatory body (CUE, KASNEB, professional boards,
etc.), and the supporting documents evidencing it.

`agency_registry` is a pluggable backend lookup (one implementation per
regulatory body) rather than a hardcoded validation rule, since each
body has its own renewal lead time and submission requirements —
`Accreditation.clean()` and `is_expiring_soon` both defer to whatever
backend `self.body` resolves to instead of encoding CUE-specific (or
any other single agency's) logic directly on the model.
"""

import datetime

from django.core.exceptions import ValidationError
from django.db import models

from base.modules.regulatory import agency_registry
from ..base import BaseModelMixin


class AccreditationDocument(BaseModelMixin):
    """
    Supporting an official Accreditation .
    """
    accreditation = models.ForeignKey(
        'Accreditation',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='accreditation_documents/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="accreditation document"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Doc for {self.accreditation.code}: {self.original_name}"


class Accreditation(BaseModelMixin):

    ACCREDITATION_TYPE_CHOICES = [
        ("Institutional", "Institutional"),
        ("Programme",      "Programme"),
        ("Specialized",    "Specialized"),
    ]

    STATUS_CHOICES = [
        ("Active",      "Active"),
        ("Pending",     "Pending"),
        ("Review",      "In Review"),
        ("Conditional", "Conditional"),
        ("Expired",     "Expired"),
    ]

    # Left blank for institution-wide accreditations (e.g. the CUE charter
    # itself), which don't belong to a single programme.
    programme = models.ForeignKey(
        'Programme',
        on_delete=models.CASCADE,
        related_name='accreditations',
        null=True,
        blank=True
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    body = models.CharField(
        max_length=30,
        choices=agency_registry.choices,
        help_text="e.g. CUE, KASNEB, Nursing Council of Kenya, Engineers Board of Kenya"
    )

    accreditation_type = models.CharField(
        max_length=20,
        choices=ACCREDITATION_TYPE_CHOICES,
        default="Programme"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    valid_from = models.DateField()
    valid_to = models.DateField(null=True)

    description = models.TextField(blank=True, default="")

    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['valid_to']

    def __str__(self):
        return f"{self.code} — {self.name}"

    def clean(self):
        super().clean()
        backend = agency_registry.get(self.body)
        if backend and self.status == "Active":
            result = backend.validate_accreditation(self)
            if not result.valid:
                raise ValidationError(result.errors)

    @property
    def is_expiring_soon(self):
        backend = agency_registry.get(self.body)
        lead_time = backend.renewal_lead_time_days() if backend else 180
        delta = (self.valid_to - datetime.date.today()).days
        return 0 <= delta <= lead_time

    @classmethod
    def expiring_within(cls, days=None):
        """
        days=None → use each accreditation's own body-specific lead time
        instead of one fixed window for every agency.
        """
        today = datetime.date.today()
        qs = cls.objects.filter(status="Active", valid_to__gte=today)
        if days is not None:
            cutoff = today + datetime.timedelta(days=days)
            return qs.filter(valid_to__lte=cutoff)
        return [a for a in qs if a.is_expiring_soon]
