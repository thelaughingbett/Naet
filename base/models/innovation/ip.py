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


class InventionDisclosure(BaseModelMixin):
    title = models.CharField(max_length=255)
    disclosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disclosures"
    )
    co_inventors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="co_disclosures",
        blank=True
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disclosures"
    )

    description = models.TextField()
    disclosure_date = models.DateField(auto_now_add=True)
    document = models.FileField(
        upload_to="ip/disclosures/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class IPRecord(BaseModelMixin):
    class IPType(models.TextChoices):
        PATENT = "patent", "Patent"
        COPYRIGHT = "copyright", "Copyright"
        TRADEMARK = "trademark", "Trademark"
        DESIGN = "design", "Design"

    class Status(models.TextChoices):
        FILED = "filed", "Filed"
        PUBLISHED = "published", "Published"
        GRANTED = "granted", "Granted"
        ABANDONED = "abandoned", "Abandoned"

    disclosure = models.ForeignKey(
        'InventionDisclosure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_records"
    )
    ip_type = models.CharField(max_length=20, choices=IPType.choices)
    application_number = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    filing_date = models.DateField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FILED
    )
    jurisdiction = models.CharField(
        max_length=100,
        blank=True
    )  # e.g. "Kenya", "PCT"

    def __str__(self):
        return f"{self.title} ({self.get_ip_type_display()})"


class LicensingAgreement(BaseModelMixin):
    ip_record = models.ForeignKey(
        'IPRecord',
        on_delete=models.CASCADE,
        related_name="licenses"
    )
    licensee_name = models.CharField(max_length=255)
    agreement_date = models.DateField()
    royalty_terms = models.TextField(blank=True)
    document = models.FileField(
        upload_to="ip/licenses/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
