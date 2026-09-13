# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from ..base import BaseModelMixin


class Idea(BaseModelMixin):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted to Startup"

    title = models.CharField(max_length=255)
    description = models.TextField()
    # e.g. HealthTech, EdTech
    domain = models.CharField(max_length=100, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ideas_submitted"
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="ideas_team_member",
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    attachment = models.FileField(
        upload_to="ideas/attachments/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class IdeaReview(BaseModelMixin):
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ]
    )

    comments = models.TextField(blank=True)
    recommended = models.BooleanField(default=False)

    class Meta:
        unique_together = ("idea", "reviewer")


class Mentor(BaseModelMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentor_profile"
    )
    # comma-separated or use M2M tag model
    expertise_areas = models.CharField(max_length=255, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    is_external = models.BooleanField(default=False)
    max_mentees = models.PositiveSmallIntegerField(default=5)

    def __str__(self):
        return self.user.get_full_name() or str(self.user)


class MentorAssignment(BaseModelMixin):
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.CASCADE,
        related_name="mentor_assignments"
    )
    mentor = models.ForeignKey(
        'Mentor',
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    assigned_on = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("idea", "mentor")
