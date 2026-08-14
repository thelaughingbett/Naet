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
import datetime

from django.db import models

from .base import (
    BaseModelMixin,
    hasUserMixin,
    id_type_choices,
)
from ..managers import (
    DeferredStudentManager,
    GraduatedStudentManager,
    ResidentStudentManager,
)

from .academic import Session

KENYAN_COUNTIES = [
    ('001', 'Mombasa'),
    ('002', 'Kwale'),
    ('003', 'Kilifi'),
    ('004', 'Tana River'),
    ('005', 'Lamu'),
    ('006', 'Taita Taveta'),
    ('007', 'Garissa'),
    ('008', 'Wajir'),
    ('009', 'Mandera'),
    ('010', 'Marsabit'),
    ('011', 'Isiolo'),
    ('012', 'Meru'),
    ('013', 'Tharaka-Nithi'),
    ('014', 'Embu'),
    ('015', 'Kitui'),
    ('016', 'Machakos'),
    ('017', 'Makueni'),
    ('018', 'Nyandarua'),
    ('019', 'Nyeri'),
    ('020', 'Kirinyaga'),
    ('021', 'Murang\'a'),
    ('022', 'Kiambu'),
    ('023', 'Turkana'),
    ('024', 'West Pokot'),
    ('025', 'Samburu'),
    ('026', 'Trans Nzoia'),
    ('027', 'Uasin Gishu'),
    ('028', 'Elgeyo Marakwet'),
    ('029', 'Nandi'),
    ('030', 'Baringo'),
    ('031', 'Laikipia'),
    ('032', 'Nakuru'),
    ('033', 'Narok'),
    ('034', 'Kajiado'),
    ('035', 'Kericho'),
    ('036', 'Bomet'),
    ('037', 'Kakamega'),
    ('038', 'Vihiga'),
    ('039', 'Bungoma'),
    ('040', 'Busia'),
    ('041', 'Siaya'),
    ('042', 'Kisumu'),
    ('043', 'Homa Bay'),
    ('044', 'Migori'),
    ('045', 'Kisii'),
    ('046', 'Nyamira'),
    ('047', 'Nairobi'),
]


class Student(BaseModelMixin, hasUserMixin):
    MARRIAGE_STATUS = [
        ("M", "Married"),
        ("U", "Unmarried"),
    ]

    stay_choices = [
        ('resident', 'Resident'),
        ('outside',  'Outside'),
    ]

    ADMISSION_PATHWAY_CHOICES = [
        ('KUCCPS', 'KUCCPS Placement'),
        ('Direct', 'Direct Self-Sponsored'),
        ('Foreign_Equivalent', 'Foreign Qualifications'),
    ]

    admission_pathway = models.CharField(
        max_length=30,
        choices=ADMISSION_PATHWAY_CHOICES,
        default='KUCCPS'
    )

    foreign_qual_cue_cert = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Mandatory if pathway is Foreign"
    )

    # --- personal info ---
    marital_status = models.CharField(
        max_length=20, choices=MARRIAGE_STATUS, default="U")
    name_of_spouse = models.CharField(max_length=255, null=True, blank=True)
    spouse_contact = models.CharField(max_length=19, null=True, blank=True)
    occupation_of_spouse = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    number_of_children = models.IntegerField(null=True, blank=True)

    id_type = models.CharField(
        max_length=24, default='national', choices=id_type_choices)
    national_id = models.CharField(
        max_length=34,
        default="xxxxxxx",
        unique=True
    )

    religion = models.CharField(max_length=34, default='pagan')
    nationality = models.CharField(max_length=34, default='Kenyan')
    ethnicity = models.CharField(max_length=34, default=' ')
    date_of_birth = models.DateField(default=datetime.date(2000, 4, 12))
    place_of_birth = models.CharField(max_length=255, default='')  # ??
    telephone_no = models.CharField(max_length=78, default='07xxxxx')
    school_email = models.EmailField(default='example@inst.com', unique=True)

    domicile = models.CharField(max_length=78, default='kenya')
    # ask  for consent or check if kenyan
    county = models.CharField(
        max_length=78,
        choices=KENYAN_COUNTIES,
        null=True,
        help_text="Required for national diversity returns"
    )
    home_address = models.CharField(
        max_length=78,
        default='kenya',
        null=True
    )

    # --- educational info ---
    registration_number = models.CharField(
        max_length=78,
        unique=True
    )

    kcse_mean_grade = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="e.g., B-plus, C-plain"
    )

    class_entered = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        related_name='class_list'
    )

    current_class = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )  # TODO  : make class entered on create
    # tracks deffered students and for analytics purposes,and graduation purposes

    disabled = models.BooleanField(default=False)  # physical disability

    disability_status = models.CharField(
        max_length=100,
        default="None",
        help_text="Specify disability type or 'None'"
    )

    stay = models.CharField(
        max_length=78,
        default='resident',
        choices=stay_choices
    )

    enrolled = models.DateTimeField(auto_now_add=True)
    deferred = models.BooleanField(default=False)

    name_of_secondary_school = models.CharField(max_length=78)
    address_of_secondary_school = models.CharField(max_length=255)

    enrollments = models.ManyToManyField(
        'Curriculum',
        related_name='enrolled_students',
        through='Enrollment',
        blank=True
    )

    def __str__(self):
        return f"{self.user.half_name} ({self.registration_number})"

    @property
    def name(self):
        return f"{self.user.half_name} ({self.registration_number})"

    @property
    def expected_graduation_session(self):
        PROGRAMME_SEMESTERS = 8

        deferred_count = self.deferments.exclude(status='withdrawn').count()
        total_semesters = PROGRAMME_SEMESTERS + deferred_count

        try:

            all_sessions = list(
                Session.objects.order_by('academic_year', 'semester')
                .values('record_id', 'academic_year', 'semester')
            )

            enrollment_session = Session.objects.filter(
                curriculum__enrollment_records__student=self,
            ).order_by('academic_year', 'semester').first()

            if not enrollment_session:
                return None

            start_idx = next(
                (i for i, s in enumerate(all_sessions)
                 if str(s['record_id']) == str(enrollment_session.record_id)),
                None
            )

            if start_idx is None:
                return None

            grad_idx = start_idx + total_semesters - 1
            if grad_idx >= len(all_sessions):
                return None

            grad_session_id = all_sessions[grad_idx]['record_id']
            return Session.objects.get(record_id=grad_session_id)

        except Exception:
            return None

    @property
    def semesters_remaining(self):
        from .academic import Session

        expected = self.expected_graduation_session
        current = Session.objects.filter(is_active=True).first()

        if not expected or not current:
            return None

        all_sessions = list(
            Session.objects.order_by('academic_year', 'semester')
            .values_list('record_id', flat=True)
        )

        try:
            current_idx = [str(s) for s in all_sessions].index(
                str(current.record_id))
            expected_idx = [str(s) for s in all_sessions].index(
                str(expected.record_id))
            return max(expected_idx - current_idx, 0)
        except ValueError:
            return None

    @property
    def is_overdue(self):
        if self.class_entered.graduated:
            return False
        remaining = self.semesters_remaining
        return remaining is not None and remaining < 0

    @property
    def current_hostel(self):
        from .academic import Session
        session = Session.objects.filter(is_active=True).first()
        if not session:
            return None
        allocation = self.hostel_allocations.filter(
            session=session, is_active=True
        ).select_related('room__hostel').first()
        return allocation.room if allocation else None

    def clean(self):
        """
        CUE Validation Rules: Foreign students must have an equation certificate.
        """
        super().clean()
        if self.admission_pathway == 'Foreign_Equivalent' and not self.foreign_qual_cue_cert:
            raise ValidationError({
                'foreign_qual_cue_cert': "A valid CUE Equation of Foreign Qualifications Certificate number is mandatory for international entries."
            })


class DeferredStudent(Student):
    """Proxy — deferred students only, separate admin view."""
    objects = DeferredStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Deferred Students'

    def reinstate(self):
        self.deferred = False
        self.save()

    @property
    def days_deferred(self):
        from django.utils import timezone
        return (timezone.now().date() - self.updated_at.date()).days


class ResidentStudent(Student):
    """Proxy — resident students only."""
    objects = ResidentStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Resident Students'


class GraduatedStudent(Student):
    """Proxy — graduated students only."""
    objects = GraduatedStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Graduated Students'


class IDCard(BaseModelMixin):
    student = models.OneToOneField(
        'Student',
        on_delete=models.CASCADE,
        related_name="id_card"
    )
    card_number = models.CharField(max_length=30, unique=True)
    issued_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(
        upload_to="registrar/id_photos/",
        blank=True,
        null=True
    )

    # an easily printable copy of the physical id issued to the student
    file = models.FileField(
        upload_to="registrar/id_file",
        blank=True,
        null=True
    )  # TODO :  in clean make this file named to students name,reg_no and date issued ,also make sure image exist's


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


# --- MODELS ---

class StudentMedicalProfile(models.Model):
    """
    Core health registry for a student. Loaded once during admission 
    and updated for long-term chronic conditions or disabilities.
    """
    student = models.OneToOneField(
        'Student',
        on_delete=models.PROTECT,
        primary_key=True,
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


class ClinicEncounter(models.Model):
    """
    Tracks day-to-day medical visits to the campus clinic or sick bay.
    """
    encounter_id = models.AutoField(primary_key=True)
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
