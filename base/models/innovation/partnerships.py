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


class IndustryPartner(BaseModelMixin):
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=150, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name


class MemorandumOfUnderstanding(BaseModelMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    partner = models.ForeignKey(
        'IndustryPartner',
        on_delete=models.CASCADE,
        related_name="mous"
    )
    title = models.CharField(max_length=255)
    signed_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    document = models.FileField(
        upload_to="partnerships/mous/",
        blank=True, null=True
    )


class AlumniEntrepreneur(BaseModelMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alumni_entrepreneur_profile"
    )
    graduation_year = models.PositiveIntegerField()
    startup_name = models.CharField(max_length=255, blank=True)
    willing_to_mentor = models.BooleanField(default=False)
    linkedin_url = models.URLField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or str(self.user)
