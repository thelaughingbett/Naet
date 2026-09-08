# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Abstract foundation shared by every concrete staff type across the
academic, administrative, and support domains: one profile shape
(status, employment type, contract/grant tracking, supervisor
hierarchy) with the role vocabulary itself left to each child.

`ROLE_CHOICES = []` is intentionally not filled in here — each child
model defines its own `role` field with its own choices, so a fresh
subclass never accidentally inherits an empty/wrong choice list.

This module is deliberately kept free of any concrete staff subclass
import: `StaffProfile.clean()` references sibling class names only as
strings (e.g. in `ALLOWED_SUPERVISOR_ROLES`, or via
`get_assigned_profile_and_role`'s dynamic `apps.get_models()` scan), so
there's no need to import Lecturer/AdministrativeStaff/etc. here and no
risk of a circular import between this module and the domain modules
that subclass it.

KNOWN ISSUE — CARRIED OVER, NOT FIXED HERE: `Meta` below constructs a
`models.UniqueConstraint(...)` but never assigns it to `constraints`,
so it has no effect — Django only picks up constraints listed in
`Meta.constraints`. Left as-is since fixing it means deciding whether
every concrete subclass actually wants a real one-user-one-profile
constraint (it plausibly does, in which case this should become
`constraints = [models.UniqueConstraint(...)]`), which is a deliberate
call rather than a drive-by fix during a reorganization.

ALSO CARRIED OVER: `ALLOWED_SUPERVISOR_ROLES` inside `clean()` (flagged
`# BUG` in the original) keys off class names `'DeptAdmin'` and
`'SchoolAdmin'`, neither of which exists — the real class is
`AdministrativeStaff` (see administrative.py). As written, a
DeptAdmin/SchoolAdmin-style supervisor restriction can never actually
trigger.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from ..base import BaseModelMixin, hasUserMixin


class StaffProfile(
    BaseModelMixin,
    hasUserMixin
):
    """
    One profile for all staff — role differentiates what they can do.
    Scope (department/school) is set via FKs, nullable depending on role.
    """

    ROLE_CHOICES = []  # override in child — child must redefine role field
    # role is intentionally NOT defined here —
    # each child defines it with their own ROLE_CHOICES
    # this avoids the empty choices list being inherited as-is

    EMPLOYMENT_TYPE_CHOICES = [
        # --- Tenured & Permanent ---
        ('tenured', 'Tenured / Permanent (Full-Time)'),
        ('probationary', 'Probationary / Tenure-Track'),

        # --- Fixed-Term & Contract ---
        ('contract_ft', 'Contract (Full-Time)'),
        ('contract_pt', 'Contract (Part-Time)'),
        ('casual', 'Casual / Day Labourer'),

        # --- Contingent, Academic-Specific & Contingent ---
        ('adjunct', 'Adjunct Faculty'),
        ('visiting', 'Visiting Scholar / Faculty'),
        ('sabbatical', 'Sabbatical Placement'),
        ('honorary', 'Honorary / Guest Appointment'),
        ('emeritus', 'Emeritus / Retired Active'),

        # --- Research & Project-Specific ---
        ('grant_funded', 'Grant-Funded / Project-Specific'),
        ('postdoc', 'Postdoctoral Fellowship'),

        # --- Internal & Student Employment ---
        ('work_study', 'Student Work-Study Program'),
        ('graduate_assistant', 'Graduate Assistantship'),

        # --- External & Outsourced ---
        ('secondment', 'Secondment / On Loan'),
        ('outsourced', 'Outsourced Third-Party Contractor'),
    ]

    STAFF_CATEGORY_CHOICES = [
        ('academic', 'Academic (Teaching & Research)'),
        ('teaching_only', 'Teaching Only / Instructional'),
        ('research_only', 'Research Only'),
        ('admin_academic', 'Admin & Academic (e.g., Dean, HOD)'),
        ('executive', 'Executive Leadership (e.g., VC, Registrar)'),
        ('admin_support', 'General Administrative Support'),
        ('finance_hr', 'Finance, HR, & Procurement'),
        ('it_technical', 'IT & Technical Support'),
        ('lab_technical', 'Laboratory & Workshop Technical'),
        ('facilities_maintenance', 'Facilities, Maintenance, & Estates'),
        ('security', 'Campus Security & Safety'),
        ('student_affairs', 'Student Affairs & Residence Life'),
        ('health_medical', 'Campus Health & Medical Services'),
        ('library', 'Library & Information Services'),
        ('hospitality_catering', 'Hospitality, Catering, & Retail'),
    ]

    STAFF_STATUS_CHOICES = [
        ('active', 'ACTIVE'),
        ('on-leave', 'On Leave'),
        ('adjunct', 'Adjunct'),
        ('inactive', 'Inactive')
    ]

    status = models.CharField(
        max_length=20,
        choices=STAFF_STATUS_CHOICES,
        default='active'
    )

    staff_number = models.CharField(max_length=20, unique=True)

    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='contract_ft'
    )

    staff_category = models.CharField(
        max_length=30,
        choices=STAFF_CATEGORY_CHOICES,
        default='academic'
    )

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_subordinates",
        limit_choices_to={'is_staff': True},
        help_text="Direct supervisor — must be an active campus staff member/admin."
    )

    date_joined = models.DateField(
        null=True,
        blank=True,
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    personal_email = models.EmailField(
        null=True,
        blank=True,
        help_text='Non-institutional email — optional'
    )

    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    alternative_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    office_location = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='e.g. Room 302, CS Building'
    )

    office_hours = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='e.g. Mon & Wed 14:00 – 16:00'
    )

    # ── contract & grant tracking ────────────────────────────────────
    contract_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Mandatory for contract-based employment types."
    )

    contract_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date this contract expires. Mandatory for contract types."
    )

    grant_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="The funding grant reference code. Mandatory if status is Grant-Funded."
    )

    grant_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date when external grant funding for this position expires."
    )

    @property
    def effective_user(self):
        """Resolves to self.user for every StaffProfile subtype except
        AdministrativeStaff, which can alternatively resolve through a
        linked Lecturer — see its override."""
        return self.user

    @property
    def is_contract_expired(self):
        """Returns True if the contract end date has passed."""
        if self.contract_end_date:
            return self.contract_end_date < timezone.now().date()
        return False

    @property
    def days_until_contract_expiry(self):
        """Calculates days remaining on the active contract."""
        if self.contract_end_date:
            delta = self.contract_end_date - timezone.now().date()
            return max(0, delta.days)
        return None

    def __init__(self, *args, **kwargs):
        """Capture the initial supervisor ID to track changes."""
        super().__init__(*args, **kwargs)
        self._initial_supervisor_id = self.supervisor_id

    class Meta:
        models.UniqueConstraint(
            fields=['user'], name='unique_%(class)s_staff_profile'
        )
        abstract = True

    def get_assigned_profile_and_role(self, user):
        """Helper method to locate a user's concrete profile and role."""
        all_staff_models = [
            model for model in apps.get_models()
            if issubclass(model, StaffProfile) and not model._meta.abstract
        ]

        for model in all_staff_models:
            related_profile_attr = f"{model.__name__.lower()}_profile"
            if hasattr(user, related_profile_attr):
                profile = getattr(user, related_profile_attr)
                return profile, profile.role

        return None, None

    def clean(self):
        """Python-level validation for forms, APIs, and Admin Panel saves."""
        """Validates supervisor hierarchy, role constraints, and prevents dual-profiles."""
        super().clean()

        if self.effective_user and not self.effective_user.is_staff:
            self.effective_user.is_staff = True
            self.effective_user.save()

        # 1. Enforce Contract Rules
        is_contract_type = self.employment_type in [
            'contract_ft',
            'contract_pt',
            'casual'
        ]

        if is_contract_type:
            if not self.contract_start_date or not self.contract_end_date:
                raise ValidationError({
                    'contract_end_date': "Contract start and end dates are mandatory for contract employment types."
                })
            if self.contract_start_date > self.contract_end_date:
                raise ValidationError({
                    'contract_end_date': "The contract end date cannot be earlier than the start date."
                })

        # 2. Enforce Grant Rules
        if self.employment_type == 'grant_funded':
            if not self.grant_number:
                raise ValidationError({
                    'grant_number': "A grant reference number is required for grant-funded positions."
                })

        if hasattr(self, 'user') and self.user:
            # Dynamically discover all concrete staff models
            all_staff_models = [
                model for model in apps.get_models()
                if issubclass(model, StaffProfile) and not model._meta.abstract
            ]

            for model in all_staff_models:
                # Skip checking the current model class being saved
                if isinstance(self, model):
                    continue

                # Construct your custom related name string: e.g., 'financestaff_profile'
                related_profile_attr = f"{model.__name__.lower()}_profile"

                # Check if the user already has this specific profile attached
                if hasattr(self.user, related_profile_attr):
                    # Fetch the existing profile class name for a clean error message
                    existing_profile_name = model._meta.verbose_name.title()
                    raise ValidationError({
                        'user': f"This user is already registered as a {existing_profile_name}. "
                        f"A user cannot hold multiple distinct staff profiles."
                    })

        if self.supervisor:
            # 1. Base User flag check
            if not self.supervisor.is_staff:
                raise ValidationError({
                    'supervisor': 'The selected supervisor user account must have is_staff=True.'
                })

            # Get a list of all subclasses inheriting from StaffProfile dynamically
            staff_models = [
                model.__name__.lower()
                for model in apps.get_models()
                if issubclass(model, StaffProfile) and not model._meta.abstract
            ]

            # Match against your specific mixin naming pattern: "%(class)s_profile"
            has_profile = any(
                hasattr(self.supervisor, f"{model_name}_profile")
                for model_name in staff_models
            )

            if not has_profile:
                raise ValidationError({
                    'supervisor': 'The selected user is marked as staff but lacks an active profile assignment.'
                })

            # 3. Self-supervision defense
            if hasattr(self, 'user') and self.supervisor == self.user:
                raise ValidationError({
                    'supervisor': 'An employee cannot be their own supervisor.'
                })

        if hasattr(self, 'supervisor') and self.supervisor and (self.supervisor_id != self._initial_supervisor_id):

            # 1. Base User flag check
            if not self.supervisor.is_staff:
                raise ValidationError({
                    'supervisor': 'The selected supervisor user account must have is_staff=True.'
                })

            # 2. Self-supervision defense
            if hasattr(self, 'user') and self.supervisor == self.user:
                raise ValidationError({
                    'supervisor': 'An employee cannot be their own supervisor.'
                })

            # 3. Locate profile and extract their role
            supervisor_profile, supervisor_role = self.get_assigned_profile_and_role(
                self.supervisor)

            if not supervisor_profile:
                raise ValidationError({
                    'supervisor': 'The selected user is marked as staff but lacks an active profile assignment.'
                })

             # 4. Enforce structural role logic
             # BUG 🪰
            ALLOWED_SUPERVISOR_ROLES = {
                'Lecturer': ['hod', 'dean', 'director'],
                'DeptAdmin': ['hod', 'school_admin', 'institution_admin'],
                'SchoolAdmin': ['dean', 'institution_admin', 'vc', 'dvc'],
                'LabTechnicalStaff': ['lab_manager', 'hod'],
                'ItStaff': ['sys_admin', 'institution_admin'],
                'FinanceStaff': ['bursar', 'accountant'],
                'LibraryStaff': ['head_librarian', 'dean'],
            }

            current_model_name = self.__class__.__name__
            allowed_roles = ALLOWED_SUPERVISOR_ROLES.get(current_model_name)

            if allowed_roles and supervisor_role not in allowed_roles:
                readable_roles = ", ".join([
                    dict(supervisor_profile.ROLE_CHOICES).get(r, r) for r in allowed_roles
                ])
                raise ValidationError({
                    'supervisor': f"Invalid supervisor assignment. A {current_model_name} can only be "
                    f"supervised by: {readable_roles}."
                })

    def __str__(self):
        return f"{self.staff_number} — {self.get_role_display()}"

    def save(self, *args, **kwargs):
        # Always run full validation cleaning before hitting the database
        self.full_clean()

        if hasattr(self, 'user') and not self.user.is_staff:
            self.user.is_staff = True
            self.user.save()

        super().save(*args, **kwargs)

        self._initial_supervisor_id = self.supervisor_id
