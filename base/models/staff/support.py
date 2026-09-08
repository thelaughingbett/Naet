# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Support / operational staff domain — every staff type that is neither
academic (teaching/research, see academic.py) nor academic-aligned
administration (see administrative.py): ordinary, permanent employment
in a specific operational function, each scoped to whichever
organizational unit makes sense for that function.

Grouped together because they share one shape — StaffProfile plus a
small `role` choice set plus at most one scope FK — and none of them
carry the leadership-appointment machinery Lecturer/AcademicAppointment
has, or the user-XOR-lecturer branching AdministrativeStaff has.

Scoping varies deliberately per type, not by oversight:
- GeneralStaff: Department OR School (exactly one, enforced in clean())
- LabTechnicalStaff: Department only (labs belong to a department)
- LibraryStaff: School only, nullable (central library staff have none)
- HostelWarden, ItStaff, FinanceStaff, MedicalStaff: no scope FK at all
  — these functions are treated as campus-wide in this schema.
"""

from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from ..base import WithDepartmentMixin, WithSchoolMixin
from .staff_profile import StaffProfile


class GeneralStaff(StaffProfile, ):
    """
    Employment-category staff with no specialized domain and no
    office/authority — department secretaries, office assistants, clerks,
    drivers, groundskeepers. Ordinary, permanent employment (same shape
    as LabTechnicalStaff/MedicalStaff/LibraryStaff), NOT an appointment —
    nobody rotates into this from being a Lecturer, and it carries no
    has_administrative_privileges flag the way AdministrativeStaff does.

    Posted to either a Department or a School, not both — unlike
    LabTechnicalStaff (department-only) or LibraryStaff (school/central).
    """

    ROLE_CHOICES = [
        ('secretary',       'Departmental / School Secretary'),
        ('office_assistant', 'Office Assistant'),
        ('clerk',            'Clerk'),
        ('driver',            'Driver'),
        ('groundskeeper',    'Groundskeeper / Facilities'),
        ('other',            'Other General Staff'),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='other'
    )

    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_set'
    )

    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_set'
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "General Staff"
        verbose_name_plural = "General Staff"

    def clean(self):
        super().clean()
        if bool(self.department_id) == bool(self.school_id):
            raise ValidationError(
                "Set exactly one of department or school — general staff "
                "are posted to one or the other, not both."
            )

    def __str__(self):
        scope = self.department or self.school
        return f"{self.staff_number} — {self.user.get_full_name()} [{self.get_role_display()}] ({scope})"


class HostelWarden(StaffProfile):
    ROLE_CHOICES = [
        ('hostel_warden', 'Hostel Warden'),
        ('assistant_warden', 'Assistant Warden'),
        ('hostel_admin',     'Hostel Administrator'),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='hostel_warden'
    )
    hostel = models.ForeignKey(
        'Hostel',
        on_delete=models.CASCADE,
        null=True
    )


class ItStaff(StaffProfile):
    ROLE_CHOICES = [
        ('net_eng', 'Network Engineer'),
        ('helpdesk', 'IT Helpdesk Support'),
        ('sysadmin', 'System Administrator'),
        ('network',  'Network Administrator'),
        ('security', 'IT Security'),
    ]
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='helpdesk'
    )


class FinanceStaff(StaffProfile):
    ROLE_CHOICES = [
        ('bursar', 'University Bursar'),
        ('accountant', 'Accountant'),
        ('cashier', 'Campus Cashier'),
        ('officer',    'Finance Officer'),
        ('auditor',    'Auditor'),
    ]
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='officer'
    )


class LabTechnicalStaff(WithDepartmentMixin, StaffProfile):
    """Handles laboratory technicians for engineering, chemistry, computing, etc."""
    ROLE_CHOICES = [
        ('lab_tech', 'Laboratory Technician'),
        ('lab_manager', 'Laboratory Manager'),
    ]
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='lab_tech'
    )


class MedicalStaff(StaffProfile):
    """Manages staff located inside the campus health unit/clinic."""
    ROLE_CHOICES = [
        ('doctor', 'Campus Medical Doctor'),
        ('nurse', 'Campus Nurse'),
        ('pharmacist', 'Pharmacist'),
    ]
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='nurse'
    )


class LibraryStaff(WithSchoolMixin, StaffProfile):
    """Manages library systems; nullable WithSchoolMixin if assigned to main library."""
    ROLE_CHOICES = [
        ('head_librarian', 'University Librarian'),
        ('library_asst', 'Library Assistant'),
    ]
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='library_asst'
    )
