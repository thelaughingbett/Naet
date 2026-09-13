# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Student medical/clinical records — the most sensitive data this app
handles (ODPC consent tracking, a data_classification field whose
'Restricted' tier is explicitly limited to Dean of Students review).
Split into its own file for that reason as much as for size: it's a
different trust boundary from the rest of student.py, not just a
different topic.

StudentMedicalProfile and ClinicEncounter now inherit BaseModelMixin
(previously plain models.Model — confirmed oversight, not intentional).
That required removing their own explicit primary keys:
  - StudentMedicalProfile.student was `primary_key=True`
  - ClinicEncounter.encounter_id was `AutoField(primary_key=True)`
BaseModelMixin is assumed to already supply an auto record_id PK (per
its use as `.record_id` elsewhere in the codebase — Session, Syllabus,
Curriculum, etc.) — two primary-key fields on one model isn't valid,
so these had to go. StudentMedicalProfile.student is now a plain
OneToOneField (still unique by definition); ClinicEncounter.encounter_id
is now a plain AutoField (still unique, just not the primary key).
"""

from django.core.exceptions import ValidationError
from django.db import models

from ..base import BaseModelMixin

# --- MEDICAL ENUMS ---
BLOOD_GROUP_CHOICES = [
    ('A+', 'A Positive'),
    ('A-', 'A Negative'),
    ('B+', 'B Positive'),
    ('B-', 'B Negative'),
    ('AB+', 'AB Positive'),
    ('AB-', 'AB Negative'),
    ('O+', 'O Positive'),
    ('O-', 'O Negative'),
    ('Unknown', 'Unknown'),
]

ENCOUNTER_TYPE_CHOICES = [
    ('Freshman_Check', 'Mandatory Initial Admission Check'),
    ('Outpatient', 'Sick Bay Walk-in Treatment'),
    ('Emergency', 'Emergency Stabilization'),
    ('Sports_Clearance', 'Athletics & Sports Medical Clearance'),
]

CLASSIFICATION_CHOICES = [
    ('Standard', 'Routine Clinical Data'),
    ('Restricted', 'Highly Sensitive / Dean of Students Review Only'),
]


class StudentMedicalProfile(BaseModelMixin):
    """
    Core health registry for a student. Loaded once during admission
    and updated for long-term chronic conditions or disabilities.
    """
    student = models.OneToOneField(
        'Student',
        on_delete=models.PROTECT,
        related_name='medical_profile'
    )

    blood_group = models.CharField(
        max_length=10,
        choices=BLOOD_GROUP_CHOICES,
        default='Unknown'
    )

    known_allergies = models.TextField(
        blank=True,
        default="None Registered",
        help_text="Food, drug, or environmental allergens"
    )

    chronic_conditions = models.TextField(
        blank=True,
        default="None",
        help_text="e.g., Asthma, Diabetes, Epilepsy"
    )

    # CUE Statutory Reporting Flags
    requires_special_accommodation = models.BooleanField(
        default=False,
        help_text="Flag for CUE disability audit requirements (e.g., ground floor hostel access, exam time extensions)"
    )

    accommodation_notes = models.TextField(blank=True, null=True)

    # ODPC Data Protection Framework Verification
    odpc_consent_signed = models.BooleanField(
        default=False,
        help_text="Mandatory under Kenyan law before processing medical history records"
    )
    consent_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Student Medical Profile"
        verbose_name_plural = "Student Medical Profiles"

    def clean(self):
        super().clean()
        if self.requires_special_accommodation and not self.accommodation_notes:
            raise ValidationError({
                'accommodation_notes': "Please detail the required institutional accommodations for CUE compliance mapping."
            })

    def __str__(self):
        return f"Medical Ledger: {self.student.student_id}"


class ClinicEncounter(BaseModelMixin):
    """
    Tracks day-to-day medical visits to the campus clinic or sick bay.
    """
    encounter_id = models.CharField(
        max_length=75,
        unique=True
    )
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='clinic_visits'
    )
    attending_clinician = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        limit_choices_to={'is_staff': True},
        help_text="The campus doctor or clinical nurse on duty"
    )
    date_of_visit = models.DateTimeField(auto_now_add=True)
    encounter_type = models.CharField(
        max_length=30,
        choices=ENCOUNTER_TYPE_CHOICES,
        default='Outpatient'
    )

    # Clinical Observations
    symptoms_reported = models.TextField()
    diagnosis = models.CharField(
        max_length=255,
        help_text="Standard medical diagnosis string"
    )
    treatment_plan = models.TextField(
        help_text="Prescribed drugs, rest orders, or hospital referral details"
    )

    # Sick Leave Tracking (Feeds into Exam Clearance Exemptions)
    recommended_sick_leave_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of class days missed. Feeds into Senate 75% attendance audit rules."
    )

    # ODPC Security Tiering
    data_classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        default='Standard'
    )

    class Meta:
        verbose_name = "Clinic Encounter Log"
        verbose_name_plural = "Clinic Encounter Logs"
        ordering = ['-date_of_visit']

    def __str__(self):
        return f"{self.encounter_type} ({self.diagnosis}) - {self.student.student_id}"
