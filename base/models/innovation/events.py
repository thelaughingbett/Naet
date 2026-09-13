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


class InnovationEvent(BaseModelMixin):
    class EventType(models.TextChoices):
        HACKATHON = "hackathon", "Hackathon"
        BOOTCAMP = "bootcamp", "Bootcamp/Workshop"
        PITCH_DAY = "pitch_day", "Pitch Day"
        COMPETITION = "competition", "Innovation Challenge"

    title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_organized"
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    banner = models.ImageField(
        upload_to="events/banners/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class EventRegistration(BaseModelMixin):
    event = models.ForeignKey(
        'InnovationEvent',
        on_delete=models.CASCADE,
        related_name="registrations"
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations"
    )
    team_name = models.CharField(max_length=150, blank=True)
    registered_on = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = ("event", "participant")
