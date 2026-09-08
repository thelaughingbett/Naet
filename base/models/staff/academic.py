# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Academic staff domain — teaching/research personnel and the leadership
appointments (HOD, Dean, Director, Exams Coordinator) that rotate
through them.

`Lecturer.role` and `AcademicAppointment.appointment_type` are kept as
two separate fields on purpose: `role` is the lecturer's *current*
standing (denormalized onto Lecturer for cheap reads/permission
checks), while `AcademicAppointment` is the auditable history of how
they got there and for how long — `AcademicAppointment.save()` is what
actually pushes a new appointment's type onto `Lecturer.role`.

`ROLE_CHOICES` intentionally mirrors `APPOINTMENT_CHOICES` plus the
baseline 'lecturer' option — comment in the original source ("make
sure they match except for ofcourse lecturer") flags that these two
lists need to be kept in sync by hand if a new leadership title is
ever added.
"""

from django.db import models
from django.core.exceptions import ValidationError

from ..base import BaseModelMixin, WithDepartmentMixin
from .staff_profile import StaffProfile


# make sure they match except for ofcourse lecturer
APPOINTMENT_CHOICES = [
    ('hod', 'Head of Department'),
    ('dean', 'Dean of Faculty'),
    ('director', 'Director of School'),
    ('exams_coordinator', 'Departmental Exams Coordinator'),
]

ROLE_CHOICES = [
    ('lecturer', 'Lecturer'),
    ('hod', 'Head of Department'),
    ('dean', 'Dean of Faculty'),
    ('director', 'Director of School'),
    ('exams_coordinator', 'Departmental Exams Coordinator'),
]


class Lecturer(WithDepartmentMixin, StaffProfile):

    academic_titles_abbreviated = [
        ("Graduate Assistant",      "GA"),
        ("Teaching Assistant",      "TA"),
        ("Tutorial Fellow",         "TF"),
        ("Assistant Lecturer",      "Asst. Lec."),
        ("Junior Lecturer",         "Jr. Lec."),
        ("Lecturer",                "Lec."),
        ("Senior Lecturer",         "Snr. Lec."),
        ("Associate Professor",     "Assoc. Prof."),
        ("Professor",               "Prof."),
        ("Full Professor",          "Full Prof."),
        ("Distinguished Professor", "Dist. Prof."),
        ("Emeritus Professor",      "Prof. Emeritus"),
        ("Adjunct Lecturer",        "Adj. Lec."),
        ("Visiting Lecturer",       "Vis. Lec."),
        ("Guest Lecturer",          "Guest Lec."),
        ("Part-Time Lecturer",      "PT Lec."),
        ("Head of Department",      "HOD"),
        ("Dean of Faculty",         "Dean"),
        ("Director of School",      "Director"),
        ("Chaired Professor",       "Chair Prof."),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='lecturer'
    )

    # ── academic identity ────────────────────────────────────────────

    title = models.CharField(
        max_length=23,
        choices=academic_titles_abbreviated,
        default='Lecturer'
    )

    specialization = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Primary teaching/research specialization'
    )

    research_interests = models.TextField(
        null=True,
        blank=True,
        help_text='Comma-separated or free text'
    )

    bio = models.TextField(
        null=True,
        blank=True,
        help_text='Short professional biography'
    )

    # ── qualifications ───────────────────────────────────────────────

    highest_degree = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='e.g. PhD in Computer Science'
    )

    degree_institution = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Institution where highest degree was obtained'
    )

    year_of_graduation = models.IntegerField(
        null=True,
        blank=True
    )

    years_of_experience = models.IntegerField(
        null=True,
        blank=True
    )

    tenured = models.BooleanField(
        default=False,
        blank=True
    )

    # ── computed properties ──────────────────────────────────────────
    @property
    def name(self):
        return f"{self.get_title_display()} {self.user.half_name}"

    @property
    def full_title(self):
        """Full display name with abbreviated title."""
        return f"{self.title} {self.user.full_name}"

    @property
    def initials(self):
        return self.user.initials

    @property
    def school_email(self):
        return self.user.email

    @property
    def is_lecturer(self): return self.role == 'lecturer'
    @property
    def is_hod(self): return self.role == 'hod'
    @property
    def is_dean(self): return self.role == 'dean'

    @property
    def research_interests_list(self):
        """Returns research interests as a Python list."""
        if not self.research_interests:
            return []
        return [r.strip() for r in self.research_interests.split(',') if r.strip()]

    @property
    def has_administrative_privileges(self):
        """HODs and Deans automatically inherit administrative approval powers."""
        return self.role in ['hod', 'dean', 'director']

    @property
    def administrative_scope(self):
        """Returns what scope this academic leader has control over."""
        if self.role == 'hod':
            return f"Department: {self.department}"
        if self.role == 'dean':
            return f"School: {self.school}"
        return "Academic Only"

    @property
    def current_appointment(self):
        """Returns their active leadership title if they have one."""
        active_appt = self.appointments.filter(is_active=True).first()
        return active_appt.get_appointment_type_display() if active_appt else "Lecturer"

    @property
    def has_administrative_privileges(self):
        """Checks if they currently hold an active leadership appointment."""
        return self.appointments.filter(is_active=True).exists()

    def __str__(self):
        return f"{self.staff_number} — {self.name}"


class AcademicAppointment(BaseModelMixin):

    lecturer = models.ForeignKey(
        'Lecturer',
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_CHOICES
    )

    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True
    )
    # TODO make false by default and only make true if appointment start date is today
    is_active = models.BooleanField(default=True)

    # NOTE: previously enforced via a UniqueConstraint on
    # (appointment_type, is_active) alone, which scoped "one active HOD"
    # to the whole institution rather than per department — wrong for any
    # department-scoped role. Moved to clean() below since Django can't
    # express "unique per lecturer__department" as a plain field-based
    # constraint without a denormalized FK.

    def save(self, *args, **kwargs):
        # Always run full validation cleaning before hitting the database
        self.full_clean()

        # TODO : make sure to return this to lecturer when appointment period elapses
        # TODO :  make this update in a background job that checks start date
        self.lecturer.role = self.appointment_type
        self.lecturer.save()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not (self.is_active and self.lecturer_id):
            return

        if self.appointment_type in ('hod', 'exams_coordinator'):
            scope = self.lecturer.department
            clashing = AcademicAppointment.objects.filter(
                appointment_type=self.appointment_type,
                is_active=True,
                lecturer__department=scope,
            ).exclude(pk=self.pk)
            if clashing.exists():
                raise ValidationError(
                    f"{scope} already has an active {self.get_appointment_type_display()}."
                )

        elif self.appointment_type in ('dean', 'director'):
            scope = self.lecturer.department.school
            clashing = AcademicAppointment.objects.filter(
                appointment_type=self.appointment_type, is_active=True,
                lecturer__department__school=scope,
            ).exclude(pk=self.pk)
            if clashing.exists():
                raise ValidationError(
                    f"{scope} already has an active {self.get_appointment_type_display()}."
                )

    def __str__(self):
        return f"{self.get_appointment_type_display()} — {self.lecturer} ({self.start_date})"
