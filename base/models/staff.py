# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0


from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from .base import (
    BaseModelMixin,
    WithDepartmentMixin,
    WithSchoolMixin,
    hasUserMixin
)


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

    ROLE_CHOICES = [
        ('lecturer', 'Lecturer'),
        ('hod', 'Head of Department'),
        ('dean', 'Dean of Faculty'),
        ('director', 'Director of School'),
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
    """
    Tracks temporary administrative appointments for Lecturers.
    """
    APPOINTMENT_CHOICES = [
        ('hod', 'Head of Department'),
        ('dean', 'Dean of Faculty'),
        ('director', 'Director of School'),
    ]

    lecturer = models.ForeignKey(
        'Lecturer',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_CHOICES
    )

    # Track the exact term of service
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Ensures a department only has ONE active HOD at any single moment
            models.UniqueConstraint(
                fields=['appointment_type', 'is_active'],
                name='unique_active_appointment_per_scope'
            )
        ]


class AdministrativeStaff(StaffProfile, WithDepartmentMixin, WithSchoolMixin):
    """
    Unified model for all academic-aligned administrative personnel 
    assisting across Departments, Schools, and central Institution structures.
    """
    ROLE_CHOICES = [
        ('vc', 'Vice-Chancellor / President'),
        ('dvc', 'Deputy Vice-Chancellor'),
        ('registrar', 'University Registrar'),
        ('dept_admin',       'Department Administrator'),
        ('school_admin',     'School / Faculty Administrator'),
        ('institution_admin', 'Central Institution Administrator'),
        ('executive_sec',    'Executive Secretary / Admin Assistant'),
        ('general_staff',    'General Administrative Staff'),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='general_staff'
    )

    has_administrative_privileges = models.BooleanField(
        default=False,
        help_text="Designates whether this admin has system approval authority over records/workflows."
    )

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
