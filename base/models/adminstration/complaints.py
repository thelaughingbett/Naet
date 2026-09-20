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
    ('Academic', 'Academic ( Lecturer Issues)'),
    ('Results', 'Results Dispute (Grade Challenge,)'),
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
    ('result_entrant', 'Result Entrant (Lecturer who recorded the score)'),
    ('lecturer_liaison', 'Programme Liaison (Lecturer, via Tclass.liason)'),
    ('Department', 'Department Level (HOD)'),
    ('school_rep', 'Student Council – School Representative'),
    ('School', 'School / Faculty Level (Dean)'),
    ('secretary_general', 'Student Council – Secretary General'),
    ('deputy_chairperson', 'Student Council – Deputy Chairperson'),
    ('chairperson', 'Student Council – Chairperson'),
    ('StudentAffairs', 'Dean of Students'),
    ('Division', 'Division Level (Registrar Academic Affairs)'),
    ('Senate', 'University Senate / Vice-Chancellor Executive'),
    ('External', 'External Body / Ombudsman / Legal Counsel'),
]

# --- ESCALATION POLICY CONFIG -------------------------------------------
#
# Results is the only category that starts at 'result_entrant' — the
# lecturer who actually recorded the disputed CAT/Exam score (Result.
# entered_by — confirm actual field name). Fastest possible fix, since
# they can correct a data-entry error directly. Academic starts one
# level later, at the programme liaison, since a "lecturer issue"
# complaint isn't about a specific score.

ESCALATION_PATHS = {
    'Academic':       ['lecturer_liaison', 'Department', 'School', 'StudentAffairs', 'Division', 'Senate'],
    'Results':        ['result_entrant', 'lecturer_liaison', 'Department', 'School', 'Division', 'Senate'],

    'Facilities':     ['school_rep', 'secretary_general', 'deputy_chairperson', 'chairperson', 'StudentAffairs', 'Senate'],
    'Administrative': ['school_rep', 'secretary_general', 'deputy_chairperson', 'chairperson', 'StudentAffairs', 'Senate'],
    'Catering':       ['school_rep', 'secretary_general', 'deputy_chairperson', 'chairperson', 'StudentAffairs', 'Senate'],
    'Other':          ['school_rep', 'secretary_general', 'deputy_chairperson', 'chairperson', 'StudentAffairs', 'Senate'],

    'Harassment':     ['StudentAffairs', 'Senate'],
}

SLA_HOURS_BY_CATEGORY = {
    'Academic':       {'default': 72, 'lecturer_liaison': 48},

    # Entrant gets the tightest window of all — it's often just a typo
    # or transcription error, so 24hr is enough to check and correct it.
    # Liaison and Division keep their existing windows.
    'Results':        {'default': 72, 'result_entrant': 24, 'lecturer_liaison': 48, 'Division': 120},

    'Facilities':     {'default': 24},
    'Administrative': {'default': 24},
    'Catering':       {'default': 24},
    'Other':          {'default': 24},

    'Harassment':     {'default': 12},
}


PRIORITY_ORDER = [
    'Low',
    'Medium',
    'High',
    'Critical'
]

RESULT_ACTION_CHOICES = [
    ('challenge', 'Challenge Result / Grade Appeal'),
]


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

    # --- results dispute linkage (category == 'Results') ---------------

    challenged_enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='complaints',
        help_text="The unit registration this grievance concerns."
    )

    challenged_result = models.ForeignKey(
        'Result',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='complaints',
        help_text="Optional: the specific CAT/Exam row disputed, when the "
        "student is challenging one component rather than the unit total."
    )

    result_action = models.CharField(
        max_length=20,
        choices=RESULT_ACTION_CHOICES,
        null=True,
        blank=True,
    )

    # Frozen at submission. The whole purpose of a challenge is that the
    # score may change; without a snapshot, an escalated case read at
    # Senate level would show the corrected score and lose the record of
    # what was actually disputed.
    snapshot_cat = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    snapshot_exam = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    snapshot_total = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    snapshot_grade = models.CharField(
        max_length=2,
        blank=True
    )
    snapshot_taken_at = models.DateTimeField(
        null=True,
        blank=True
    )

    date_opened = models.DateTimeField(
        auto_now_add=True
    )
    # TODO : auto escalation based on work policy so that after a given while if complaint is not resolved it goes  higher up , just for annoying purposes ✅
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

    history = HistoricalRecords()

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

        if self.category == 'Results':
            if not self.challenged_enrollment_id:
                raise ValidationError({
                    'challenged_enrollment': "A results dispute must reference the unit being disputed."
                })
            if not self.result_action:
                raise ValidationError({
                    'result_action': "Specify whether this is a challenge, resit request, or missing-marks report."
                })
        elif self.challenged_enrollment_id or self.challenged_result_id:
            raise ValidationError(
                "Only a 'Results' grievance should carry a result reference."
            )

        # The student can only dispute their own enrollment — without this,
        # a crafted POST could attach someone else's marks to a complaint and
        # expose them to every officer in the escalation chain.
        if (
            self.challenged_enrollment_id
            and self.challenged_enrollment.student_id != self.student_id
        ):
            raise ValidationError({
                'challenged_enrollment': "You can only dispute your own results."
            })

        if (
            self.challenged_result_id
            and self.challenged_result.enrollment_id != self.challenged_enrollment_id
        ):
            raise ValidationError({
                'challenged_result': "The disputed result doesn't belong to the referenced unit registration."
            })

    def _take_result_snapshot(self):
        """Freeze the disputed scores as they stood when the student filed."""
        from base.models import Result

        published = Result.objects.filter(
            enrollment_id=self.challenged_enrollment_id,
            type__in=['C', 'E'],
            state='published',
        ).order_by('record_id')

        scores = {r.type: r.score for r in published}
        cat = scores.get('C')
        exam = scores.get('E')

        self.snapshot_cat = cat
        self.snapshot_exam = exam
        if cat is not None or exam is not None:
            total = (cat or 0) + (exam or 0)
            self.snapshot_total = total
            self.snapshot_grade = (
                'A' if total >= 70 else
                'B' if total >= 60 else
                'C' if total >= 50 else
                'D' if total >= 40 else 'F'
            )
        self.snapshot_taken_at = timezone.now()

    def save(self, *args, **kwargs):
        if self.status == 'Resolved' and not self.date_resolved:
            self.date_resolved = timezone.now()
        elif self.status != 'Resolved':
            self.date_resolved = None

        is_new = self._state.adding

        if is_new and not self.current_level:
            path = self.escalation_path
            idx = self._resolve_level(path, 0)
            self.current_level = path[idx]
            self.sla_due_at = timezone.now() + timezone.timedelta(
                hours=get_sla_hours(self.category, self.current_level)
            )

        if is_new and self.category == 'Results' and self.challenged_enrollment_id:
            self._take_result_snapshot()

        super().save(*args, **kwargs)

        if is_new and self.result_action == 'challenge' and self.challenged_enrollment_id:
            from base.models import Result
            qs = Result.objects.filter(
                enrollment_id=self.challenged_enrollment_id,
                state='published',
            )
            if self.challenged_result_id:
                qs = qs.filter(pk=self.challenged_result_id)
            qs.update(state='disputed')

    def _bump_priority(self):
        idx = PRIORITY_ORDER.index(self.priority)
        self.priority = PRIORITY_ORDER[min(idx + 1, len(PRIORITY_ORDER) - 1)]

    def escalate(self, by_user=None, reason="", automatic=False, new_priority=None):
        if not automatic and by_user is None:
            raise ValidationError(
                "A manual escalation requires the escalating user.")

        path = self.escalation_path
        try:
            current_idx = path.index(self.current_level)
        except ValueError:
            current_idx = -1

        if current_idx + 1 >= len(path):
            if automatic and self.priority != 'Critical':
                self._bump_priority()
                self.save(update_fields=['priority'])
            return None

        next_idx = self._resolve_level(path, current_idx + 1)
        next_level = path[next_idx]

        reason_text = reason or (
            "SLA window expired" if automatic else "Manually escalated"
        )
        skipped = path[current_idx + 1: next_idx]
        if skipped:
            skipped_labels = ", ".join(
                dict(LEVEL_CHOICES).get(lvl, lvl) for lvl in skipped
            )
            reason_text += f" (seat vacant, skipped: {skipped_labels})"

        history = ComplaintEscalationHistory(
            complaint=self,
            escalated_from_level=self.current_level,
            escalated_to_level=next_level,
            escalated_by=None if automatic else by_user,
            is_automatic=automatic,
            reason_for_escalation=reason_text,
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

    @property
    def result_dispute_context(self):
        """Everything a reviewing officer needs, without re-deriving it per view."""
        if self.category != 'Results' or not self.challenged_enrollment_id:
            return None

        enr = self.challenged_enrollment
        course = enr.curriculum.course

        return {
            'course_code':    course.course_code,
            'course_name':    course.course_name,
            'credits':        course.credits,
            'session':        str(enr.curriculum.session),
            'lecturers': [
                a.lecturer.name
                for a in enr.curriculum.lecturer_assignments.select_related('lecturer__user')
            ],
            'action':         self.get_result_action_display(),
            'at_filing': {
                'cat':   self.snapshot_cat,
                'exam':  self.snapshot_exam,
                'total': self.snapshot_total,
                'grade': self.snapshot_grade,
                'as_of': self.snapshot_taken_at,
            },
            'current': [
                {'type': r.get_type_display(), 'score': r.score, 'state': r.state}
                for r in enr.results.filter(type__in=['C', 'E']).order_by('record_id')
            ],
        }

    # --- rep lookup helpers ---------------------------------------------

    @property
    def _tclass(self):
        """
        The student's current class — holds `liason` (programme liaison)
        and `student_rep` (class rep). TODO: confirm the actual FK name
        from Student to Tclass; adjust the getattr chain below if it's
        called something other than these.
        """
        return (
            getattr(self.student, 'current_class', None)
            or getattr(self.student, 'tclass', None)
            or getattr(self.student, 'Tclass', None)
        )

    @property
    def _school(self):
        tclass = self._tclass
        if not tclass or not tclass.programme_id:
            return None
        department = tclass.programme.department  # via WithDepartmentMixin
        return getattr(department, 'school', None)

    def _has_level_holder(self, level):
        if level == 'result_entrant':
            if not self.challenged_result_id:
                # No single Result row pinned (dispute is at the
                # enrollment/unit level) — nothing to check, skip to liaison.
                return False
            entrant_id = getattr(self.challenged_result, 'entered_by_id', None)
            return bool(entrant_id)

        if level == 'lecturer_liaison':
            tclass = self._tclass
            return bool(tclass and tclass.liason_id)

        if level == 'Department':
            department = getattr(self._tclass.programme,
                                 'department', None) if self._tclass else None
            return bool(department)

        if level == 'school_rep':
            school = self._school
            if not school:
                return False
            from base.models.studentCouncil import CouncilPosition
            return CouncilPosition.objects.filter(
                school=school, position='school_rep', is_active=True
            ).exists()

        if level == 'School':
            school = self._school
            return bool(school)

        if level in ('secretary_general', 'deputy_chairperson', 'chairperson'):
            from base.models.studentCouncil import CouncilPosition, CouncilTerm
            term = CouncilTerm.current()
            return bool(term) and CouncilPosition.objects.filter(
                term=term, position=level, is_active=True
            ).exists()

        return True

    def _resolve_level(self, path, start_idx):
        """
        Walk forward from `start_idx` past any level whose seat is
        currently vacant, and land on the first one that's actually
        held. If every remaining level in the path is vacant, stop at
        the last one — there's nowhere further to fall back to.
        """
        idx = start_idx
        while idx < len(path) - 1 and not self._has_level_holder(path[idx]):
            idx += 1
        return idx


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
                "A complaint cannot be escalated to the exact same administrative tier."
            )
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
