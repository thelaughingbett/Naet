# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Administrative staff domain — academic-aligned admin personnel who
assist across Departments, Schools, and central Institution structures
(registrars, VC/DVC office, department/school administrators, general
admin staff).

The `user` XOR `lecturer` split on `AdministrativeStaff` covers two
different kinds of person holding this role: a career administrator
(pure `user`) versus a sitting academic who has also taken on an admin
role (`lecturer`, whose own `User` is reached via `effective_user`).
That's why `effective_user` here — unlike the plain passthrough on
`StaffProfile` — has to resolve through either path.

KNOWN ISSUE — CARRIED OVER, NOT FIXED HERE: `clean()` and `__str__()`
below branch on `self.role in ('dept_admin', 'school_admin',
'institution_admin')`, but none of those three strings appear in
`ADMIN_ROLE_CHOICES` — the actual choices are `hod`, `dean`,
`director`, `vc`, `dvc`, `registrar`, `director_of_exams`,
`executive_sec`, `general_staff`. As written, those scope-enforcement
branches can never fire for a role value that actually validates
against the field's own choices. Left unresolved since the fix depends
on which side is wrong — whether `ADMIN_ROLE_CHOICES` is missing
`dept_admin`/`school_admin`/`institution_admin`, or `clean()` should
be checking `hod`/`dean`/`director` instead.
"""

from django.db import models
from django.core.exceptions import ValidationError

from ..base import WithDepartmentMixin, WithSchoolMixin
from .staff_profile import StaffProfile


ADMIN_ROLE_CHOICES = [
    ('vc', 'Vice-Chancellor / President'),
    ('dvc', 'Deputy Vice-Chancellor'),
    ('registrar', 'University Registrar'),
    ('director_of_exams', 'Director of Examinations'),
    ('hod', 'Head of Department'),
    ('dean', 'Dean of Faculty'),
    ('director', 'Director of School'),
    ('executive_sec', 'Executive Secretary / Admin Assistant'),
    ('general_staff', 'General Administrative Staff'),
]


class AdministrativeStaff(StaffProfile, WithDepartmentMixin, WithSchoolMixin):
    """
    Unified model for all academic-aligned administrative personnel 
    assisting across Departments, Schools, and central Institution structures.
    """

    role = models.CharField(
        max_length=30,
        choices=ADMIN_ROLE_CHOICES,
        default='general_staff'
    )

    # override the mixin's required field
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    lecturer = models.ForeignKey(
        'Lecturer',
        null=True,
        blank=True,
        on_delete=models.CASCADE, related_name='administrative_appointments'
    )

    has_administrative_privileges = models.BooleanField(
        default=False,
        help_text="Designates whether this admin has system approval authority over records/workflows."
    )

    @property
    def effective_user(self):
        return self.user or (self.lecturer.user if self.lecturer_id else None)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'], name='unique_%(class)s_staff_profile'
            )
        ]
        verbose_name = "Administrative Staff Profile"
        verbose_name_plural = "Administrative Staff Profiles"

    def clean(self):
        """Enforces scope integrity based on the selected administrative role."""
        super().clean()

        if bool(self.user_id) == bool(self.lecturer_id):
            raise ValidationError(
                "Set exactly one of user or lecturer — a career "
                "administrator uses user directly; a sitting academic "
                "taking on this role links via lecturer instead."
            )

        # ── Scope Enforcement Logic ─────────────────────────────────
        if self.role == 'dept_admin':
            if not getattr(self, 'department_id', None):
                raise ValidationError({
                    'department': 'A Department Administrator must be explicitly assigned to a Department.'
                })
            # Ensure the school matches the department's parent school automatically if available
            if hasattr(self, 'department') and self.department and hasattr(self.department, 'school'):
                self.school = self.department.school

        elif self.role == 'school_admin':
            if not getattr(self, 'school_id', None):
                raise ValidationError({
                    'school': 'A School Administrator must be explicitly assigned to a School / Faculty.'
                })
            # Clear department field because their scope covers the whole school
            self.department = None

        elif self.role in ['institution_admin', 'general_staff']:
            # Central administrators and general floaters can span the whole campus;
            # we make lower-level scopes optional or clear them based on your business rules.
            # Here we clear them to maintain a clean database slate.
            self.department = None
            self.school = None

    def __str__(self):
        scope = ""
        if self.role == 'dept_admin' and self.department:
            scope = f" ({self.department.code})"
        elif self.role == 'school_admin' and self.school:
            scope = f" ({self.school.code})"

        return f"{self.staff_number} — {self.user.get_full_name()} [{self.get_role_display()}{scope}]"
