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

from django.core.exceptions import ValidationError
from .base import BaseModelMixin
from django.db import models
from base.models import Session
from .student import Student


class Timetable(BaseModelMixin):

    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.PROTECT,
        related_name='timetable_slots'
    )

    # TODO : move this to settings.py
    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    # TODO : move this to settings.py
    TIME_SLOTS = [
        ('08:00-10:00', '1st Slot (08:00 - 10:00)'),
        ('10:00-12:00', '2nd Slot (10:00 - 12:00)'),
        ('12:00-13:00', '3rd Slot (12:00 - 13:00)'),
        ('13:00-15:00', '4th Slot (13:00 - 15:00)'),
        ('15:00-17:00', '5th Slot (15:00 - 17:00)'),
        ('17:00-19:00', '6th Slot (17:00 - 19:00)'),
    ]

    TIMETABLE_SLOT_TYPE_CHOICES = [
        ('Lecture', 'Regular Lecture Class'),
        ('Practical', 'Practical / Laboratory Session'),
        ('CAT', 'Continuous Assessment Test (CAT)'),
        ('Tutorial', 'Tutorial / Discussion Group'),
    ]

    slot_type = models.CharField(
        max_length=15,
        choices=TIMETABLE_SLOT_TYPE_CHOICES,
        default='Lecture',
        db_index=True,
        help_text="Tracks session allocation styles required for specialized capacity audits."
    )

    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    time_slot = models.CharField(max_length=11, choices=TIME_SLOTS)

    venue = models.ForeignKey(
        "Venue",
        on_delete=models.DO_NOTHING,
        related_name="timetable_slots"
    )

    class Meta:
        unique_together = [
            # Prevent a cohort from being split into two slots at once
            ('curriculum', 'day', 'time_slot'),
            # Prevent double-booking a single physical venue space
            ('venue', 'day', 'time_slot'),
        ]
        verbose_name = "Master Timetable Slot"
        verbose_name_plural = "Master Timetable Slots"

    def clean(self):
        """
        Compliance Audit: Verifies space limitations and facility traits 
        against the designated slot requirements.
        """
        super().clean()

        if self.venue_id and self.curriculum_id:
            # 1. Computer Lab Resource Safe-Check
            # If the class is flagged as a Practical/Lab session, ensure the assigned venue actually has computers.
            if self.slot_type == 'Practical' and not self.venue.has_computers:
                raise ValidationError({
                    'venue': f"Resource Defieciency: Cannot assign a 'Practical' slot type to '{self.venue.venue_name}' "
                    f"because this venue record indicates it lacks computer/lab workstations."
                })

            # 2. Strict Class Capacity Guardrail
            # Ensure the cohort student size (Tclass size) does not exceed the maximum physical sitting limits of the venue.
            # Assuming a student_count tracker exists on Tclass
            cohort_size = self.curriculum.Tclass.student_count
            if cohort_size > self.venue.capacity:
                raise ValidationError({
                    'venue': f"Capacity Breach: The cohort class size ({cohort_size} students) exceeds "
                    f"the maximum legal capacity of '{self.venue.venue_name}' ({self.venue.capacity} seats)."
                })

    def __str__(self):
        return f"{self.curriculum.course.course_code} ({self.slot_type}) — {self.day} [{self.time_slot}]"


EXECUTION_STATUS_CHOICES = [
    ('Scheduled', 'Scheduled (Default state for the day)'),
    ('Attended', 'Attended / Successfully Taught'),
    ('Missed', 'Missed / Lecturer No-Show'),
    ('Cancelled', 'Cancelled / General University Holiday'),
    ('Rescheduled', 'Rescheduled to a New Slot'),
]

RESCHEDULE_INITIATOR_CHOICES = [
    ('LECTURER', 'Requested by Assigned Faculty/Lecturer'),
    ('STUDENT', 'Requested by Student Cohort / Class Rep'),
    ('ADMIN', 'Enforced by University Administration'),
]


class DailyClassExecution(BaseModelMixin):
    """
    Tracks the actual day-to-day execution and attendance of a timetable slot.
    Feeds directly into CUE quality audits for class contact-hour verification.
    """
    timetable_slot = models.ForeignKey(
        'Timetable',
        on_delete=models.PROTECT,
        related_name='daily_executions'
    )

    # The actual calendar date for this specific lecture instance
    calendar_date = models.DateField(db_index=True)

    # Updated to point directly to the list variable
    status = models.CharField(
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='Scheduled',
        db_index=True
    )

    # --- STUDENT ATTENDANCE CONFIRMATION ENGINE ---
    class_representative = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='confirmed_daily_classes',
        null=True,
        blank=True,
        help_text="The Class Representative or student who signs off/vouchers that the class took place."
    )

    student_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True
    )

    # --- RESCHEDULING ENGINE METRICS ---
    rescheduled_by = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name='initiated_class_reschedules',
        null=True,
        blank=True,
        help_text="The staff user (lecturer/admin) who processed the adjustment in the system."
    )

    # Updated to point directly to the list variable
    reschedule_requested_by_role = models.CharField(
        max_length=15,
        choices=RESCHEDULE_INITIATOR_CHOICES,
        null=True,
        blank=True,
        help_text="Tracks whether the request came from the lecturer or the student group."
    )

    # The new target coordinates if status == 'Rescheduled'
    rescheduled_to_date = models.DateField(null=True, blank=True)
    rescheduled_to_time_slot = models.CharField(
        max_length=11,
        choices=Timetable.TIME_SLOTS,  # Reuses choices array from your main Timetable class
        null=True,
        blank=True
    )

    rescheduled_to_venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='rescheduled_classes',
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True,
        help_text="Reasoning for cancellation or rescheduling parameters."
    )

    class Meta:
        unique_together = ('timetable_slot', 'calendar_date')
        verbose_name = "Daily Class Execution"
        verbose_name_plural = "Daily Class Executions"
        ordering = ['-calendar_date']

    def clean(self):
        """
        Enforces strict logical guardrails over class sign-offs and reschedule moves.
        """
        super().clean()

        # 1. Verification Guardrail
        if self.status == 'Attended':
            if not self.class_representative:
                raise ValidationError({
                    'class_representative': "CUE Academic Audit Rule: Cannot log a lecture instance as 'Attended' "
                                            "without assigning a verifying Student representative code."
                })
            if not self.student_confirmed_at:
                from django.utils import timezone
                self.student_confirmed_at = timezone.now()

        # 2. Rescheduling Data Integrity Guardrail
        if self.status == 'Rescheduled':
            if not self.rescheduled_by or not self.reschedule_requested_by_role:
                raise ValidationError({
                    'rescheduled_by': "Please document the user and requesting role initiating this reschedule event."
                })
            if not self.rescheduled_to_date or not self.rescheduled_to_time_slot or not self.rescheduled_to_venue:
                raise ValidationError({
                    'rescheduled_to_date': "You must complete all target fields (Date, Time, and Venue) when moving a class."
                })

            # Prevent moving a class onto the exact same coordinates
            if (self.calendar_date == self.rescheduled_to_date and
                self.timetable_slot.time_slot == self.rescheduled_to_time_slot and
                    self.timetable_slot.venue == self.rescheduled_to_venue):
                raise ValidationError(
                    "Invalid Reschedule: Target coordinates match the original slot parameters.")

    def __str__(self):
        return f"{self.calendar_date} : {self.timetable_slot.curriculum.course.course_code} -> [{self.get_status_display()}]"

# TODO : make sure when curriculum is set an exam session is defined but date kept empty and any strategy takes this into consideration


class ExamSession(BaseModelMixin):
    """A single exam sitting."""

    # TODO : move this to settings.py
    TIME_SLOTS = [
        ('08:00-11:00', '1st Slot (08:00 – 11:00)'),
        ('11:00-14:00', '2nd Slot (11:00 – 14:00)'),
        ('14:00-17:00', '3rd Slot (14:00 – 17:00)'),
        ('17:00-20:00', '4th Slot (17:00 – 20:00)'),
        ('20:00-23:00', '5th Slot (20:00 – 23:00)'),
    ]

    TYPE_CHOICES = [
        ('CAT',  'CAT'),
        ('MAIN', 'Main Exam'),
        ('SUPP', 'Supplementary'),
        ('SPECIAL', 'Special / Supplementary'),
        ('PRACTICAL', 'Practical'),
    ]

    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='exam_sessions'
    )  # when generating timetable common unit should be a concern here ,should be unique or not consider supp or unique together with type

    exam_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )
    date = models.DateField(null=True)
    time_slot = models.CharField(
        max_length=11,
        choices=TIME_SLOTS,
        null=True
    )

    class Meta:
        # one exam type per curriculum entry (course+class+session)
        unique_together = ('curriculum', 'exam_type')

    def __str__(self):
        return (
            f"{self.curriculum.course.course_code}"
            f" - {self.exam_type}"
            f" - {self.curriculum.session}"
        )

    @property
    def slot_start(self):
        """Returns '08:00' from '08:00-11:00'"""
        return self.time_slot.split('-')[0]

    @property
    def slot_end(self):
        """Returns '11:00' from '08:00-11:00'"""
        return self.time_slot.split('-')[1]

    @classmethod
    def detect_clashes_for_student(cls, student, session):
        """Find all exam time conflicts for a student in a session."""
        enrollments = student.enrollment_records.filter(
            curriculum__session=session,
            status='approved'
        ).values_list('curriculum_id', flat=True)

        exam_sessions = cls.objects.filter(
            curriculum_id__in=enrollments
        ).order_by('date', 'time_slot')

        clashes = []
        exam_list = list(exam_sessions)

        for i, exam_a in enumerate(exam_list):
            for exam_b in exam_list[i+1:]:
                # same date + same time_slot = clash
                if exam_a.date == exam_b.date and exam_a.time_slot == exam_b.time_slot:
                    clashes.append((exam_a, exam_b))

        return clashes

    @classmethod
    def detect_all_clashes(cls, session):
        """Run clash detection for all students in a session."""
        students = Student.objects.filter(
            enrollment_records__curriculum__session=session,
            enrollment_records__status='approved'
        ).distinct()

        for student in students:
            clashes = cls.detect_clashes_for_student(student, session)
            for exam_a, exam_b in clashes:
                ExamClash.objects.get_or_create(
                    student=student,
                    session_a=exam_a,
                    session_b=exam_b
                )


INVIGILATOR_ROLE_CHOICES = [
    ('Chief', 'Chief Invigilator (Room Lead)'),
    ('Assistant', 'Assistant Invigilator'),
    ('Relief', 'Relief / Floating Invigilator'),
]


class ExamVenue(BaseModelMixin):
    """
    Maps a specific physical space to an exam session slot.
    Supports a scalable squad of invigilators via an explicit through-table.
    """
    exam_session = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='venues'
    )

    venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='exam_venues'
    )

    invigilators = models.ManyToManyField(
        'Lecturer',
        through='ExamInvigilatorAssignment',
        related_name='assigned_exam_venues',
        blank=True
    )

    class Meta:
        unique_together = ('exam_session', 'venue')
        verbose_name = "Exam Venue Slot"
        verbose_name_plural = "Exam Venue Slots"

    def __str__(self):
        return f"{self.exam_session} at {self.venue}"


# --- ADDED STATUS CHOICES ---
INVIGILATOR_ASSIGNMENT_STATUS_CHOICES = [
    ('Draft', 'Draft Assignment (Internal Planning)'),
    ('Published', 'Published / Notified (Lecturer Alerted)'),
    ('Confirmed', 'Confirmed / Accepted by Lecturer'),
    ('Excused', 'Excused / Absent with Apology'),
    ('Present', 'Present / Duty Executed (Exam Day Checked)'),
    ('Absent', 'Absent Without Apology (Flagged for HR review)'),
]


class ExamInvigilatorAssignment(BaseModelMixin):
    """
    Intermediary through-table linking lecturers to an ExamVenue slot.
    Tracks duty scheduling states, structural hierarchy, and attendance compliance.
    """
    exam_venue = models.ForeignKey(
        'ExamVenue',
        on_delete=models.CASCADE,
        related_name='invigilator_assignments'
    )

    lecturer = models.ForeignKey(
        'Lecturer',
        on_delete=models.PROTECT,
        related_name='exam_assignments'
    )

    role = models.CharField(
        max_length=20,
        choices=INVIGILATOR_ROLE_CHOICES,
        default='Assistant'
    )

    status = models.CharField(
        max_length=20,
        choices=INVIGILATOR_ASSIGNMENT_STATUS_CHOICES,
        default='Draft',
        db_index=True,
        help_text="Tracks the scheduling lifecycle and actual attendance on exam day."
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam_venue', 'lecturer')
        verbose_name = "Exam Invigilating Duty"
        verbose_name_plural = "Exam Invigilating Duties"

    def clean(self):
        """
        Operational Guardrails: Checks calendar collisions, status exceptions, 
        and leadership conflicts before saving.
        """
        super().clean()

        if self.exam_venue_id and self.lecturer_id:
            session = self.exam_venue.exam_session

            # 1. Smart Calendar Conflict Engine
            # Bugfix/Optimization: Only check for double-booking clashes if the assignment
            # is active ('Draft', 'Published', 'Confirmed', 'Present').
            # If the lecturer is 'Excused' or 'Absent', they are no longer occupying that time slot,
            # allowing the system to schedule a replacement lecturer without errors.
            active_statuses = ['Draft', 'Published', 'Confirmed', 'Present']

            if self.status in active_statuses:
                clash = ExamInvigilatorAssignment.objects.filter(
                    lecturer=self.lecturer,
                    exam_venue__exam_session__date=session.date,
                    exam_venue__exam_session__time_slot=session.time_slot,
                    status__in=active_statuses
                ).exclude(pk=self.pk)

                if clash.exists():
                    raise ValidationError({
                        'lecturer': f"Scheduling Clash: {self.lecturer} is already active "
                        f"at room '{clash.first().exam_venue.venue}' during this time block."
                    })

            # 2. Chief Leader Constraint Gatekeeper
            if self.role == 'Chief' and self.status in active_statuses:
                clashing_chiefs = ExamInvigilatorAssignment.objects.filter(
                    exam_venue=self.exam_venue,
                    role='Chief',
                    status__in=active_statuses
                ).exclude(pk=self.pk)

                if clashing_chiefs.exists():
                    raise ValidationError({
                        'role': f"Leadership Conflict: '{self.exam_venue.venue}' already has an active Chief Invigilator. "
                        f"Please register subsequent staff as Assistants."
                    })

    def __str__(self):
        return f"{self.lecturer} ({self.role}) - [{self.get_status_display()}]"


class ExamClash(BaseModelMixin):
    """Records detected exam clashes for a student."""

    # consider this when checking for student retakes and how to deal with that
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='exam_clashes'
    )

    session_a = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='clashes_a'
    )

    session_b = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='clashes_b'
    )

    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Clash for {self.student} — {self.session_a} vs {self.session_b}"


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


class ExamCard(BaseModelMixin):
    """
    Represents an issued exam admit card for a student in a session.
    Serial number and QR payload are generated once and reused —
    regenerating creates a new ExamCard record (old one is superseded).

    A student can only have ONE active card per session.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='exam_cards'
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.PROTECT,
        related_name='exam_cards'
    )

    serial_number = models.CharField(max_length=30, unique=True)

    is_active = models.BooleanField(default=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    last_printed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('student', 'session', 'is_active')
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.serial_number} — {self.student.registration_number} ({self.session})"

    @classmethod
    def generate_serial(cls):
        # TODO : change this to a strategy
        """UNI-2026-XXXX-XXXX format, guaranteed unique."""
        import random
        from datetime import datetime

        while True:
            year = datetime.now().year
            r1 = str(random.randint(0, 9999)).zfill(4)
            r2 = str(random.randint(0, 9999)).zfill(4)
            serial = f"UNI-{year}-{r1}-{r2}"
            if not cls.objects.filter(serial_number=serial).exists():
                return serial

    @property
    def qr_payload(self):
        """String encoded into the QR — verifiable at exam halls."""
        return f"{self.student.registration_number}|{self.serial_number}|{self.session}"
