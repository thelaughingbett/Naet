# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from django.core.exceptions import ValidationError
from django.utils import timezone
from .base import BaseModelMixin
from django.db import models
from simple_history.models import HistoricalRecords


from django.conf import settings


class DefermentDocument(BaseModelMixin):
    """
    Supporting document uploaded alongside a deferment request.
    One deferment can have multiple attachments.
    """
    deferment = models.ForeignKey(
        'Deferment',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='deferments/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    uploaded_by_user = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='uploaded_deferment_docs',
        null=True  # TODO :  remove this
    )

    def __str__(self):
        return f"{self.original_name} → {self.deferment}"


class Deferment(BaseModelMixin):
    """
    Records each individual deferment event for a student.
    A student may defer multiple times — each gets its own record.
    """

    REASON_CHOICES = [
        ('financial',   'Financial Difficulty'),
        ('medical',     'Medical'),
        ('personal',    'Personal'),
        ('academic',    'Academic'),
        ('other',       'Other'),
    ]

    STATUS_CHOICES = [
        ('active',      'Active'),
        ('reinstated',  'Reinstated'),
        ('withdrawn',   'Withdrawn'),
    ]

    # Approval workflow — separate from the deferment status itself
    REQUEST_STATUS_CHOICES = [
        ('pending',   'Pending Review'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='deferments'
    )
    session_deferred = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='deferments',
        help_text='The session the student deferred from'
    )
    session_returning = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='returning_students',
        null=True,
        blank=True,
        help_text='The session the student is expected to return'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='personal'
    )
    reason_detail = models.TextField(
        null=True,
        blank=True,
        help_text='Free text from student or registrar'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )
    request_status = models.CharField(
        max_length=10,
        choices=REQUEST_STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='approved_deferments',
        null=True,
        blank=True,
    )
    reinstated_at = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"


class Reporting(BaseModelMixin):

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='reportings',
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name='reportings'
    )

    REPORTED_VIA_CHOICES = [
        ("online", "Online"),
        ("physical", "Physical")
    ]

    reported_at = models.DateTimeField(
        auto_now_add=True
    )

    reported_via = models.CharField(
        max_length=10,
        choices=REPORTED_VIA_CHOICES
    )

    history = HistoricalRecords()

    class Meta:
        # can't report twice in same session
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student} - {self.session}"


class HostelListing(BaseModelMixin):
    """
    External hostel listing for the student hostel guide.
    These are off-campus options — not the same as the Hostel model
    which tracks on-campus rooms and allocations.
    """

    BADGE_CHOICES = [
        ('popular',   '⭐ Popular'),
        ('students',  '👩‍🎓 Students only'),
        ('scenic',    '🏞️ Scenic'),
        ('community', '🤝 Community'),
        ('views',     '🌅 Great views'),
        ('other',     'Other'),
    ]

    ROOM_TYPE_CHOICES = [
        ('single',         'Single'),
        ('single_ensuite', 'Single en-suite'),
        ('shared_2',       '2–4 sharing'),
        ('shared_4',       '4–6 sharing'),
        ('studio',         'Studio & shared'),
        ('mixed',          'Single & shared'),
    ]

    name = models.CharField(max_length=120)
    badge = models.CharField(
        max_length=20,
        choices=BADGE_CHOICES,
        null=True,
        blank=True
    )

    location = models.CharField(
        max_length=255,
        help_text='Street address and landmark'
    )
    distance_note = models.CharField(
        max_length=120,
        help_text='e.g. 2 min walk to North Gate'
    )

    price_per_month = models.PositiveIntegerField(help_text='KES per month')
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES
    )

    # amenity toggles — rendered as chips in the template
    has_wifi = models.BooleanField(default=True)
    has_meals = models.BooleanField(default=False)
    has_laundry = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_kitchen = models.BooleanField(default=False)
    has_study_rooms = models.BooleanField(default=False)
    has_lounge = models.BooleanField(default=False)
    has_bike_storage = models.BooleanField(default=False)
    has_ethernet = models.BooleanField(default=False)
    wifi_note = models.CharField(
        max_length=60,
        blank=True,
        help_text='e.g. High-speed, WiFi + study rooms'
    )

    phone = models.CharField(max_length=20)
    email = models.EmailField()

    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text='Lower = appears first'
    )

    class Meta:
        ordering = ['sort_order', 'price_per_month']

    def __str__(self):
        return self.name

    @property
    def amenity_chips(self):
        """Returns a list of (icon, label) tuples for template rendering."""
        chips = []
        wifi_label = self.wifi_note or 'WiFi included'
        if self.has_wifi:
            chips.append(('📶', wifi_label))
        if self.has_meals:
            chips.append(('🍽️', 'Meal plan optional'))
        if self.has_laundry:
            chips.append(('🧺', 'Laundry on site'))
        if self.has_gym:
            chips.append(('🏋️', 'Gym access'))
        if self.has_parking:
            chips.append(('🅿️', 'Free parking'))
        if self.has_kitchen:
            chips.append(('🍳', 'Kitchen access'))
        if self.has_study_rooms:
            chips.append(('📚', 'Study rooms'))
        if self.has_lounge:
            chips.append(('🎮', 'Common lounge'))
        if self.has_bike_storage:
            chips.append(('🚲', 'Bike storage'))
        if self.has_ethernet:
            chips.append(('🔌', 'WiFi + ethernet'))
        return chips


# --- LOGICAL CHOICES ---
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

# --- THE ATTACHMENT SYSTEM ---


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
            ext = os.path.splitext(self.file.name).lower()
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

    class Meta:
        verbose_name = "Student Complaint"
        verbose_name_plural = "Student Complaints"
        ordering = ['-date_opened']

    def clean(self):
        """
        Operational Validation Guardrails.
        """
        super().clean()

        # Enforce case resolution tracking
        if self.status == 'Resolved' and not self.resolution_remarks:
            raise ValidationError({
                'resolution_remarks': "CUE audit guidelines require capturing a text resolution remark before closing a student file."
            })

        # Automatic Severity Assignment for extreme safety cases
        if self.category == 'Harassment' and self.priority != 'Critical':
            self.priority = 'Critical'

    def save(self, *args, **kwargs):
        # Automate resolution timestamps dynamically based on state changes
        if self.status == 'Resolved' and not self.date_resolved:
            self.date_resolved = timezone.now()
        elif self.status != 'Resolved':
            self.date_resolved = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.category}] {self.subject[:30]}... ({self.status})"


LEVEL_CHOICES = [
    ('Department', 'Department Level (HOD / Lecturer)'),
    ('School', 'School / Faculty Level (Dean)'),
    ('Division', 'Division Level (Registrar Academic Affairs)'),
    ('Senate', 'University Senate / Vice-Chancellor Executive'),
    ('External', 'External Body / Ombudsman / Legal Counsel'),
]


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

    escalated_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='initiated_escalations',
        help_text="The staff member who triggered this upward movement"
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

    def __str__(self):
        return f"Escalation {self.id}: {self.escalated_from_level} → {self.escalated_to_level}"


# --- CUE STANDARDIZED GRADUATION CLASSIFICATIONS ---
CLASSIFICATION_CHOICES = [
    ('First_Class', 'First Class Honours / Distinction'),
    ('Second_Upper', 'Second Class Honours (Upper Division)'),
    ('Second_Lower', 'Second Class Honours (Lower Division)'),
    ('Pass', 'Pass (Standard Undergraduate or Postgraduate award)'),
    ('Satisfied', 'Satisfied ( Doctorates/PhDs)'),
]


class Graduation(BaseModelMixin):
    """
    Data register mapped directly to CUE's graduation data return specifications.
    Tracks academic award distributions across cohorts.
    """

    graduation_status = [
        ("nominated", "Nominated"),
        ("verified", "Verified"),
        ("approved", "Approved"),
        ("conferred", "Conferred")
    ]
    student = models.OneToOneField(
        'Student',
        on_delete=models.PROTECT,
        related_name="graduation_candidacy"
    )

    Tclass = models.ForeignKey(
        "TClass",
        on_delete=models.PROTECT,
        related_name="graduation_candidates"
    )  # graduated with class of

    status = models.CharField(
        max_length=20,
        choices=graduation_status,
        default='nominated'
    )

    final_classification = models.CharField(
        max_length=30,
        choices=CLASSIFICATION_CHOICES,
        help_text="Official degree classification mapped to CUE data guidelines."
    )

    with_honours = models.BooleanField(
        default=True,
        help_text="Flag indicating if the degree was conferred with an Honours distinction."
    )

    thesis_title = models.TextField(
        blank=True,
        null=True,
        help_text="Compulsory for Postgraduate (Masters/PhD) returns"
    )

    class Meta:
        verbose_name = "Graduation Record"
        verbose_name_plural = "Graduation Records"

    def clean(self):
        """
        CUE Verification Rule: Postgraduates must have a thesis title registered, 
        and Doctorates do not carry standard Honours flags.
        """
        super().clean()

        # Guardrail: Check if the student belongs to a Postgraduate track via their program layout

        # TODO :  replace to check class if it is a phd class
        if hasattr(self.student, 'enrolments'):
            latest_enrolment = self.student.enrolments.order_with_respect_to(
                'year_of_study'
            ).last()
            if latest_enrolment and latest_enrolment.program.program_code.upper().startswith(('MSC', 'PHD', 'MA')):

                # Check 1: Mandatory thesis titles for higher degrees
                if not self.thesis_title:
                    raise ValidationError({
                        'thesis_title': "CUE quality data returns require a verified Thesis/Dissertation title for all Postgraduate awards."
                    })

                # Check 2: Adjust Honours logic for Doctorates if accidentally checked true
                if latest_enrolment.program.program_code.upper().startswith('PHD') and self.with_honours:
                    raise ValidationError({
                        'with_honours': "Doctoral/PhD programs are not awarded with Honours designations under standard guidelines."
                    })

    def __str__(self):
        return f"Graduated: {self.student.registration_number} ({self.Tclass}) - {self.get_final_classification_display()}"


class StatusChangeRequest(BaseModelMixin):
    class ChangeType(models.TextChoices):
        LEAVE_OF_ABSENCE = "leave", "Leave of Absence"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        READMISSION = "readmission", "Readmission"
        PROGRAM_TRANSFER = "program_transfer", "Program Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="status_change_requests"
    )
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices
    )
    reason = models.TextField(blank=True)
    supporting_document = models.FileField(
        upload_to="registrar/status_changes/",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes_processed"
    )
    effective_date = models.DateField(null=True, blank=True)


class DegreeAudit(BaseModelMixin):
    class Result(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        DEFICIENT = "deficient", "Deficient"
        ELIGIBLE = "eligible", "Eligible for Graduation"

    student = models.OneToOneField(
        'Student',
        on_delete=models.CASCADE,
        related_name="degree_audit"
    )
    credits_completed = models.PositiveIntegerField(default=0)
    credits_remaining = models.PositiveIntegerField(default=0)
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.ON_TRACK
    )

    last_reviewed = models.DateTimeField(auto_now=True)


class Diploma(BaseModelMixin):
    candidacy = models.OneToOneField(
        'Graduation',
        on_delete=models.CASCADE,
        related_name="diploma"
    )
    diploma_number = models.CharField(max_length=50, unique=True)
    conferred_date = models.DateField()
    issued = models.BooleanField(default=False)
    file = models.FileField(
        upload_to="registrar/diplomas/",
        blank=True,
        null=True
    )


class Convocation(BaseModelMixin):
    name = models.CharField(max_length=150)  # e.g. "42nd Convocation"
    date = models.DateField()
    venue = models.CharField(max_length=255, blank=True)
    candidates = models.ManyToManyField(
        'Graduation',
        related_name="convocations",
        blank=True
    )
