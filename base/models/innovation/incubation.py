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


class Cohort(BaseModelMixin):
    name = models.CharField(max_length=100)  # e.g. "Cohort 2026-A"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Startup(BaseModelMixin):
    class Stage(models.TextChoices):
        IDEATION = "ideation", "Ideation"
        MVP = "mvp", "MVP"
        EARLY_TRACTION = "early_traction", "Early Traction"
        GROWTH = "growth", "Growth"
        GRADUATED = "graduated", "Graduated"
        DISCONTINUED = "discontinued", "Discontinued"

    name = models.CharField(max_length=255)
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startups"
    )

    cohort = models.ForeignKey(
        'Cohort',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startups"
    )

    founders = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="startups_founded"
    )
    sector = models.CharField(max_length=100, blank=True)
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.IDEATION
    )
    incorporation_date = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to="startups/logos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


class Milestone(BaseModelMixin):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DELAYED = "delayed", "Delayed"

    startup = models.ForeignKey(
        'Startup',
        on_delete=models.CASCADE,
        related_name="milestones"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    class Meta:
        ordering = ["due_date"]


class Resource(BaseModelMixin):
    """Physical resource: lab, co-working desk, meeting room, equipment."""
    class Kind(models.TextChoices):
        LAB = "lab", "Lab"
        WORKSPACE = "workspace", "Workspace/Desk"
        MEETING_ROOM = "meeting_room", "Meeting Room"
        EQUIPMENT = "equipment", "Equipment"

    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


class ResourceBooking(BaseModelMixin):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    resource = models.ForeignKey(
        'Resource',
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bookings"
    )
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_bookings"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )

    class Meta:
        ordering = ["-start_time"]
