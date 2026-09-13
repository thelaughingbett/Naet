# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Facilities domain — the physical campus: buildings and the individual
rooms/halls/labs inside them, plus the accessibility and equipment
facts other domains need to make scheduling decisions.

Deliberately its own subpackage rather than folded into scheduling/ or
exams/: a Venue is referenced by both `scheduling.Timetable` (regular
classes) and `exams.exam_scheduling.ExamVenue` (exam sittings), so it
belongs to neither and is a shared dependency of both instead.
"""

from django.db import models
from django.core.exceptions import ValidationError

from ..base import BaseModelMixin


class Building(BaseModelMixin):
    """
    Represents a physical block or structure on the university campus.
    Tracks core structural assets required for CUE infrastructure returns.
    """
    building_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g., Science Complex, Phase 2 Block"
    )
    building_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="e.g., SCI, ADM, LIB"
    )

    total_floors = models.PositiveIntegerField(default=1)

    has_lift = models.BooleanField(
        default=False,
        verbose_name="Has Functional Lift/Elevator",
        help_text="Crucial for calculating upper floor accessibility defaults."
    )

    has_ramp_access = models.BooleanField(
        default=False,
        verbose_name="Has Ground Floor Ramp Access",
        help_text="Verifies wheelchair entry points into the physical block."
    )

    is_exam_venue = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.building_name} ({self.building_code})"


class Venue(BaseModelMixin):
    """
    Represents an individual room, lecture hall, lab, or auditorium inside a building.
    """
    building = models.ForeignKey(
        "Building",
        on_delete=models.PROTECT,
        related_name='venues',
        help_text="The physical structure housing this specific venue."
    )

    capacity = models.IntegerField(
        help_text="Maximum sitting capacity approved for student allocations."
    )

    venue_name = models.CharField(
        max_length=34,
        unique=True,
        help_text="e.g., SCI 101, Auditorium A"
    )

    floor = models.PositiveIntegerField(
        default=0,
        help_text="0 for Ground Floor, 1 for First Floor, etc."
    )  # for checks with students with disability

    # --- CUE ACCREDITATION & FACILITY AUDIT FIELDS ---
    has_projector = models.BooleanField(
        default=False,
        verbose_name="Projector Available",
        help_text="Is a fixed digital projector installed in the room?"
    )

    has_smartboard = models.BooleanField(
        default=False,
        verbose_name="Smartboard Installed",
        help_text="Is an interactive digital smartboard present?"
    )

    has_audio_system = models.BooleanField(
        default=False,
        verbose_name="Audio System",
        help_text="Includes built-in microphones, amplifiers, or sound speakers."
    )

    has_computers = models.BooleanField(
        default=False,
        verbose_name="Computers Available",
        help_text="Equipped with student workstations (e.g., for ICT/Computer Lab audits)."
    )

    is_accessible = models.BooleanField(
        default=False,
        verbose_name="Accessible (Ramps/Lifts)",
        help_text="Mandatory CUE/ODPC compliance flag for wheelchair and disability accessibility."
    )

    has_whiteboard = models.BooleanField(
        default=True,  # Default True since almost every lecture room has a basic board
        verbose_name="Whiteboard Available",
        help_text="Standard writing whiteboard or chalkboard is mounted."
    )

    def clean(self):
        """
        Structural Integrity Engine: Automates and cross-references floor layout validation
        against parent building configurations.
        """
        super().clean()

        if self.building:
            # 1. Floor Bound Guardrail
            if self.floor >= self.building.total_floors:
                raise ValidationError({
                    'floor': f"Invalid floor assignment. {self.building.building_name} only has {self.building.total_floors} floors (Indices 0 to {self.building.total_floors - 1})."
                })

            # 2. Automated Disability Accessibility Logic Check
            # Ground floor (floor=0) only needs a ramp at the building entrance to be accessible.
            if self.floor == 0 and self.building.has_ramp_access:
                self.is_accessible = True
            # Upper floors can ONLY be wheelchair-accessible if the building itself features an active lift.
            elif self.floor > 0 and not self.building.has_lift:
                if self.is_accessible:
                    raise ValidationError({
                        'is_accessible': "Compliance Validation Error: Upper-floor venues cannot be marked accessible if the parent building structure lacks a functional elevator system."
                    })
                self.is_accessible = False

    def __str__(self):
        return f"{self.venue_name} - {self.capacity}"
