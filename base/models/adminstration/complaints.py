# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin

# --- LOGICAL CHOICES ---------------------------------------------------

COMPLAINT_CATEGORY_CHOICES = [
    ('Academic', 'Academic (Missing Marks, Exam Appeals, Lecturer Issues)'),
    ('Harassment', 'Harassment / Gender-Based Violence (Strict Confidentiality)'),
    ('Administrative', 'Administrative (Finance Portal, Admissions, Registration)'),
    ('Facilities', 'Facilities & Accommodation (Hostel Damage, Wi-Fi, Water)'),
    ('Catering', 'Catering & Health Services (Mess issues, Sick Bay complaints)'),
    ('Other', 'General / Unclassified Grievance'),
]

PRIORITY_CHOICES = [
    ('Low', 'Low Priority'),
    ('Medium', 'Medium Priority'),
    ('High', 'High Priority'),
    ('Critical', 'Critical / Emergency'),
]

STATUS_CHOICES = [
    ('Open', 'Grievance Logged / Pending Review'),
    ('In_Progress', 'Under Active Investigation'),
    ('Escalated', 'Escalated to University Senate / Legal Counsel'),
    ('Resolved', 'Resolution Achieved / Case Closed'),
]

UPLOAD_ROLE_CHOICES = [
    ('student', 'Uploaded by Student (Evidence)'),
    ('officer', 'Uploaded by Resolving Officer / Staff (Official Action/Report)'),
]

LEVEL_CHOICES = [
    ('Department', 'Department Level (HOD / Lecturer)'),
    ('School', 'School / Faculty Level (Dean)'),
    ('StudentAffairs', 'Dean of Students'),
    ('Division', 'Division Level (Registrar Academic Affairs)'),
    ('Senate', 'University Senate / Vice-Chancellor Executive'),
    ('External', 'External Body / Ombudsman / Legal Counsel'),
]

# --- ESCALATION POLICY CONFIG -------------------------------------------
#
# category -> ordered list of levels the complaint climbs through.
# Index 0 is where a new complaint starts; escalate() walks forward.
#
# Ops categories (Facilities/Administrative/Catering/Other) start at
# 'School' because the School Student Rep is the front-line handler
# before anything reaches Dean of Students. Harassment skips both
# Department and School entirely.

ESCALATION_PATHS = {
    'Academic':       ['Department', 'School', 'StudentAffairs', 'Division', 'Senate'],
    'Facilities':     ['School', 'StudentAffairs', 'Senate'],
    'Administrative': ['School', 'StudentAffairs', 'Senate'],
    'Catering':       ['School', 'StudentAffairs', 'Senate'],
    'Other':          ['School', 'StudentAffairs', 'Senate'],
    'Harassment':     ['StudentAffairs', 'Senate'],
}

# category -> hours allowed at a level before the SLA is breached.
# 'default' covers any level not explicitly listed for that category.

SLA_HOURS_BY_CATEGORY = {
    'Academic':       {'default': 72},
    'Facilities':     {'default': 48},
    'Administrative': {'default': 48},
    'Catering':       {'default': 24},
    'Other':          {'default': 72},
    'Harassment':     {'default': 12},   # tight window, deliberately
}

PRIORITY_ORDER = ['Low', 'Medium', 'High', 'Critical']


def get_sla_hours(category, level):
    bucket = SLA_HOURS_BY_CATEGORY.get(category, {'default': 72})
    return bucket.get(level, bucket['default'])


# --- THE ATTACHMENT SYSTEM ----------------------------------------------

class ComplaintDocument(BaseModelMixin):
    """
    Supporting evidence or documentation uploaded alongside a complaint file.
    Can be used by students for screenshots/PDF evidence, or by officers
    for investigation reports/signed clearance memos.
    """
    complaint = models.ForeignKey(
        'Complaint',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='complaints/%Y/%m/')
    original_name = models.CharField(
        max_length=255,
        blank=True
    )

    # Track who provided this piece of documentation for the audit trail
    uploaded_by_role = models.CharField(
        max_length=10,
        choices=UPLOAD_ROLE_CHOICES,
        default='student'
    )

    uploaded_by_user = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='uploaded_complaint_docs'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """
        Validates files to ensure the system safely processes both raw mobile
        screenshots and formal document uploads.
        """
        super().clean()
        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            # Dynamic allowance array for easy mobile/desktop usability
            allowed_extensions = [
                '.pdf',
                '.png',
                '.jpg',
                '.jpeg',
                '.webp',
                '.heic',
                '.doc',
                '.docx'
            ]  # include video but limit size e.g 25mbs and delete after a while after resolution and or allow or give hints for linking video through urls
            # TODO :  use python magic here also this is a security risk ,consider checking before saving or flag as potential malware

            if ext not in allowed_extensions:
                raise ValidationError(
                    f"Unsupported file format '{ext}'. The system only accepts PDFs, Word documents, "
                    f"and standard images/screenshots ({', '.join(allowed_extensions)})."
                )

    def save(self, *args, **kwargs):
        # Automatically preserve the human-readable filename before Django saves it to disk
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_uploaded_by_role_display()}] {self.original_name}"


class Complaint(BaseModelMixin):
    """
    University Grievance Ledger mapped to CUE institutional governance
    and ODPC student privacy compliance parameters.
    """
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='complaints'
    )

    category = models.CharField(
        max_length=45,
        choices=COMPLAINT_CATEGORY_CHOICES
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='Medium'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Open'
    )

    subject = models.CharField(
        max_length=255,
        help_text="Brief headline of the grievance"
    )

    description = models.TextField(
        help_text="Detailed context of the issue"
    )

    assigned_staff = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_grievances'
    )  # based on category i.e academic assigned first to HOD -> Registrar, harrasment ,admin to dean then escalated  or other wise ,facilities to dean who then pushes to hostel warden or otherwise,general to dean

    resolution_remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Official closure summary"
    )

    history = HistoricalRecords()

    date_opened = models.DateTimeField(auto_now_add=True)
    # TODO : auto escalation based on work policy so that after a given while if comlaint is not resolves it goes the higher up , jus for annoying purposes
    date_resolved = models.DateTimeField(blank=True, null=True)

    is_anonymous_to_faculty = models.BooleanField(
        default=False,
        help_text="Hides identity from departmental lecturers; visible only to the Dean of Students."
    )

    current_level = models.CharField(
        max_length=30,
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
        help_text="Where in this category's escalation path the complaint "
        "currently sits. Set on first save, advanced by escalate()."
    )

    sla_due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the current level's SLA window expires. The "
        "scheduled job escalates anything with sla_due_at in "
        "the past and status != 'Resolved'."
    )

    class Meta:
        verbose_name = "Student Complaint"
        verbose_name_plural = "Student Complaints"
        ordering = ['-date_opened']

    @property
    def escalation_path(self):
        return ESCALATION_PATHS.get(self.category, ['School', 'StudentAffairs', 'Senate'])

    def clean(self):
        super().clean()

        if self.status == 'Resolved' and not self.resolution_remarks:
            raise ValidationError({
                'resolution_remarks': "CUE audit guidelines require capturing a text resolution remark before closing a student file."
            })

        if self.category == 'Harassment' and self.priority != 'Critical':
            self.priority = 'Critical'

    def save(self, *args, **kwargs):
        if self.status == 'Resolved' and not self.date_resolved:
            self.date_resolved = timezone.now()
        elif self.status != 'Resolved':
            self.date_resolved = None

        if self._state.adding and not self.current_level:
            self.current_level = self.escalation_path[0]
            self.sla_due_at = timezone.now() + timezone.timedelta(
                hours=get_sla_hours(self.category, self.current_level)
            )

        super().save(*args, **kwargs)

    def _bump_priority(self):
        idx = PRIORITY_ORDER.index(self.priority)
        self.priority = PRIORITY_ORDER[min(idx + 1, len(PRIORITY_ORDER) - 1)]

    def escalate(self, by_user=None, reason="", automatic=False, new_priority=None):
        """
        Moves the complaint to the next level in its category's path.

        automatic=True  -> system/Celery call. escalated_by is left null,
                            priority is bumped one tier automatically.
        automatic=False -> a human is escalating early. by_user is
                            required, and THEY set the priority (via
                            new_priority) rather than it being auto-bumped.
        """
        if not automatic and by_user is None:
            raise ValidationError(
                "A manual escalation requires the escalating user.")

        path = self.escalation_path
        try:
            current_idx = path.index(self.current_level)
        except ValueError:
            current_idx = -1

        if current_idx + 1 >= len(path):
            # Already at the top of this category's ladder (Senate/External).
            # Nothing further to escalate to — flag it rather than raise,
            # so a Celery loop doesn't choke on a stale-but-maxed complaint.
            if automatic and self.priority != 'Critical':
                self._bump_priority()
                self.save(update_fields=['priority'])
            return None

        next_level = path[current_idx + 1]

        history = ComplaintEscalationHistory(
            complaint=self,
            escalated_from_level=self.current_level,
            escalated_to_level=next_level,
            escalated_by=None if automatic else by_user,
            is_automatic=automatic,
            reason_for_escalation=reason or (
                "SLA window expired" if automatic else "Manually escalated"
            ),
        )
        history.full_clean()
        history.save()

        self.current_level = next_level
        self.status = 'Escalated'
        self.sla_due_at = timezone.now() + timezone.timedelta(
            hours=get_sla_hours(self.category, next_level)
        )

        if automatic:
            self._bump_priority()
        elif new_priority:
            self.priority = new_priority

        self.save()
        return history

    def __str__(self):
        return f"[{self.category}] {self.subject[:30]}... ({self.status})"


class ComplaintEscalationHistory(models.Model):
    """
    Tracks the sequential movements of a complaint as it is pushed
    up the university administrative hierarchy.
    """
    complaint = models.ForeignKey(
        'Complaint',
        on_delete=models.CASCADE,
        related_name='escalation_history'
    )

    escalated_from_level = models.CharField(
        max_length=30,
        choices=LEVEL_CHOICES
    )

    escalated_to_level = models.CharField(max_length=30, choices=LEVEL_CHOICES)

    # Nullable so a system-triggered escalation doesn't need to invent a
    # human actor.
    escalated_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='initiated_escalations',
        null=True,
        blank=True,
        help_text="Null when is_automatic=True — the Celery job escalated this, not a person."
    )

    is_automatic = models.BooleanField(
        default=False,
        help_text="True if a scheduled job escalated this because the SLA "
        "expired; False if a staff member escalated it manually."
    )

    date_escalated = models.DateTimeField(auto_now_add=True)
    reason_for_escalation = models.TextField(
        help_text="Why the issue could not be resolved at the lower administrative level"
    )

    class Meta:
        verbose_name = "Complaint Escalation Record"
        verbose_name_plural = "Complaint Escalation Records"
        # Oldest to newest to show a clean chronological chain
        ordering = ['date_escalated']

    def clean(self):
        super().clean()
        if self.escalated_from_level == self.escalated_to_level:
            raise ValidationError(
                "A complaint cannot be escalated to the exact same administrative tier.")
        if self.is_automatic and self.escalated_by_id:
            raise ValidationError({
                'escalated_by': "An automatic escalation shouldn't carry a human actor. "
                "Set is_automatic=False if a staff member actually triggered this."
            })
        if not self.is_automatic and not self.escalated_by_id:
            raise ValidationError({
                'escalated_by': "A manual escalation requires the staff member who triggered it."
            })

    def __str__(self):
        who = "system" if self.is_automatic else str(self.escalated_by)
        return f"Escalation {self.id}: {self.escalated_from_level} → {self.escalated_to_level} ({who})"
