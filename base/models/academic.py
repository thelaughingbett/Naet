# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from base.modules.regulatory import agency_registry
import os
from django.core.exceptions import ValidationError
from django.db import models
import datetime
import re

import magic

from django.db import models, transaction


from .base import (
    BaseModelMixin,
    WithDepartmentMixin,
    WithSchoolMixin
)

UNESCO_ISCED_FIELDS = [
    # 00 Generic Programmes and Qualifications
    ('0011', 'Basic programmes and qualifications'),
    ('0021', 'Literacy and numeracy'),
    ('0031', 'Personal skills and development'),
    ('0099', 'Generic programmes and qualifications not elsewhere classified'),

    # 01 Education
    ('0111', 'Education science'),
    ('0112', 'Training for pre-school teachers'),
    ('0113', 'Teacher training without subject specialisation'),
    ('0114', 'Teacher training with subject specialisation'),
    ('0188', 'Inter-disciplinary programmes involving education'),

    # 02 Arts and Humanities
    ('0211', 'Audio-visual techniques and media production'),
    ('0212', 'Fashion, interior and industrial design'),
    ('0213', 'Fine arts'),
    ('0214', 'Handicrafts'),
    ('0215', 'Music and performing arts'),
    ('0221', 'Religion and theology'),
    ('0222', 'History and archaeology'),
    ('0223', 'Philosophy and ethics'),
    ('0231', 'Language acquisition'),
    ('0232', 'Literature and linguistics'),
    ('0288', 'Inter-disciplinary programmes involving arts and humanities'),

    # 03 Social Sciences, Journalism and Information
    ('0311', 'Economics'),
    ('0312', 'Political sciences and civics'),
    ('0313', 'Psychology'),
    ('0314', 'Sociology and cultural studies'),
    ('0321', 'Journalism and reporting'),
    ('0322', 'Library, information and archival studies'),
    ('0388', 'Inter-disciplinary programmes involving social sciences/journalism'),

    # 04 Business, Administration and Law
    ('0411', 'Accounting and taxation'),
    ('0412', 'Finance, banking and insurance'),
    ('0413', 'Management and administration'),
    ('0414', 'Marketing and advertising'),
    ('0415', 'Secretarial and office work'),
    ('0416', 'Wholesale and retail sales'),
    ('0417', 'Work skills'),
    ('0421', 'Law'),
    ('0488', 'Inter-disciplinary programmes involving business/admin/law'),

    # 05 Natural Sciences, Mathematics and Statistics
    ('0511', 'Biology'),
    ('0512', 'Biochemistry'),
    ('0521', 'Environmental sciences'),
    ('0522', 'Natural environments and wildlife'),
    ('0531', 'Chemistry'),
    ('0532', 'Earth sciences'),
    ('0533', 'Physics'),
    ('0541', 'Mathematics'),
    ('0542', 'Statistics'),
    ('0588', 'Inter-disciplinary programmes involving natural sciences/maths'),

    # 06 Information and Communication Technologies (ICTs)
    ('0611', 'Computer use (Basic IT/Applications)'),
    ('0612', 'Database and network design and administration'),
    ('0613', 'Software and applications development and analysis (Computer Science)'),
    ('0688', 'Inter-disciplinary programmes involving ICTs'),

    # 07 Engineering, Manufacturing and Construction
    ('0711', 'Chemical engineering and processes'),
    ('0712', 'Environmental protection technology'),
    ('0713', 'Electricity and energy'),
    ('0714', 'Electronics and automation (Mechatronics/Hardware Engineering)'),
    ('0715', 'Mechanics and metal trades'),
    ('0716', 'Motor vehicles, ships and aircraft (Aeronautical/Automotive)'),
    ('0721', 'Food processing'),
    ('0722', 'Materials (glass, paper, plastic and wood)'),
    ('0723', 'Textiles (clothes, footwear and leather)'),
    ('0724', 'Mining and extraction'),
    ('0731', 'Architecture and town planning'),
    ('0732', 'Building and civil engineering'),
    ('0788', 'Inter-disciplinary programmes involving engineering/construction'),

    # 08 Agriculture, Forestry, Fisheries and Veterinary
    ('0811', 'Crop and livestock production'),
    ('0812', 'Horticulture'),
    ('0821', 'Forestry'),
    ('0831', 'Fisheries'),
    ('0841', 'Veterinary'),
    ('0888', 'Inter-disciplinary programmes involving agriculture/veterinary'),

    # 09 Health and Welfare
    ('0911', 'Dental studies'),
    ('0912', 'Medicine (Clinical Medicine/Surgery/MBChB)'),
    ('0913', 'Nursing and midwifery'),
    ('0914', 'Medical diagnostic and treatment technology (Radiology/Lab Tech)'),
    ('0915', 'Therapy and rehabilitation (Physiotherapy)'),
    ('0916', 'Pharmacy'),
    ('0917', 'Traditional and complementary medicine and therapy'),
    ('0921', 'Care of elderly and of disabled adults'),
    ('0922', 'Child care and youth services'),
    ('0923', 'Social work and counselling'),
    ('0988', 'Inter-disciplinary programmes involving health and welfare'),

    # 10 Services
    ('1011', 'Domestic services'),
    ('1012', 'Hair and beauty services'),
    ('1013', 'Hotel, restaurants and catering'),
    ('1014', 'Sports'),
    ('1015', 'Travel, tourism and leisure'),
    ('1021', 'Community sanitation'),
    ('1022', 'Occupational health and safety'),
    ('1031', 'Military science and defence'),
    ('1032', 'Protection of persons and property (Security Management/Police)'),
    ('1041', 'Transport services (Logistics/Aviation operations)'),
    ('1088', 'Inter-disciplinary programmes involving services'),
]


class Institution(BaseModelMixin):
    active_session = models.ForeignKey(
        'Session',
        on_delete=models.DO_NOTHING
    )

    institution_name = models.CharField(max_length=123)
    logo = models.ImageField(upload_to='logo/')

    charter_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class School(BaseModelMixin):
    school_name = models.CharField(max_length=78)

    active_session = models.ForeignKey(
        'Session',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"school of {self.school_name}"


# TODO : reconsider the with school mixin
class Department(WithSchoolMixin, BaseModelMixin):
    department_name = models.CharField(max_length=123)

    def __str__(self):
        return f"Department of {self.department_name}"


class Programme(BaseModelMixin, WithDepartmentMixin):
    kenyan_degrees = [
        ("BSc",    "Bachelor of Science"),
        ("BEd",    "Bachelor of Education"),
        ("LLB",    "Bachelor of Laws"),
        ("BA",     "Bachelor of Arts"),
        ("BCom",   "Bachelor of Commerce"),
        ("BBIT",   "Bachelor of Business Information Technology"),
        ("B.Arch", "Bachelor of Architecture"),
        ("BEng",   "Bachelor of Engineering"),
        ("MBChB",  "Bachelor of Medicine and Bachelor of Surgery"),
        ("BPharm", "Bachelor of Pharmacy"),
        ("BDS",    "Bachelor of Dental Surgery"),
        ("PGDE",   "Post Graduate Diploma in Education"),
        ("MSc",    "Master of Science"),
        ("MA",     "Master of Arts"),
        ("MBA",    "Master of Business Administration"),
        ("LLM",    "Master of Laws"),
        ("MEd",    "Master of Education"),
        ("MPH",    "Master of Public Health"),
        ("PhD",    "Doctor of Philosophy"),
        ("MD",     "Doctor of Medicine"),
    ]

    LEVEL_CHOICES = [
        ("Undergraduate", "Undergraduate"),
        ("Postgraduate",  "Postgraduate"),
        ("Diploma",        "Diploma"),
        ("Certificate",    "Certificate"),
    ]

    STATUS_CHOICES = [
        ("Active",   "Active"),
        ('Expired', 'Expired'),
        ('Suspended', 'Suspended'),
        ('Review', 'Under Review')
    ]

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    programme_name = models.CharField(
        max_length=255,
        unique=True,
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="Undergraduate"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="Active"
    )

    description = models.TextField(
        blank=True,
        default=""
    )

    degree_type = models.CharField(
        max_length=123,
        choices=kenyan_degrees
    )

    current_class = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        related_name='current_class',
        null=True,
        blank=True
    )  # refers to the most recent enrolling class , TODO :  this should change to somehing

    # approved_cue_capacity ,TODO : should be based on accredition or some form of strategy
    capacity = models.IntegerField(default=70)

    unesco_isced = models.CharField(
        max_length=123,
        null=True,
        blank=True,
        choices=UNESCO_ISCED_FIELDS,
        help_text="Standardized UNESCO tag for this specific subject matter."
    )

    kuccps_programme_code = models.CharField(
        max_length=7,
        unique=True,
        null=True,
        blank=True
    )  # e.g., "1279115"

    duration_years = models.IntegerField(default=4)
    semesters_per_year = models.IntegerField(default=2)
    total_credits_required = models.PositiveIntegerField(default=120)

    @property
    def total_semesters(self):
        return self.duration_years * self.semesters_per_year

    def __str__(self):
        return self.programme_name


class Tclass(BaseModelMixin):
    class_name = models.CharField(max_length=78)

    programme = models.ForeignKey('Programme', on_delete=models.PROTECT)

    courses = models.ManyToManyField('Course', through='Curriculum')

    year_of_study = models.IntegerField(default=1, null=True, blank=True)

    graduated = models.DateField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.class_name


class Session(BaseModelMixin):
    SEMESTER_CHOICES = [
        ("1", "Semester 1"),
        ("2", "Semester 2"),
        ("3", "Semester 3"),
    ]

    academic_year = models.CharField(max_length=9)  # e.g. "2024/2025"
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True)
    registration_start = models.DateField(null=True, blank=True)
    registration_end = models.DateField(null=True, blank=True)
    # is this redundant given that active session is set in school ? 👇🏿
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('academic_year', 'semester')

    def __str__(self):
        return f"{self.academic_year} - Sem {self.semester}"

    @property
    def progress(self):
        today = datetime.datetime.now().date()
        if today <= self.start_date:
            return 0
        if today >= self.end_date:
            return 100
        total_days = (self.end_date - self.start_date).days
        days_passed = (today - self.start_date).days
        if total_days <= 0:
            return 100
        return round((days_passed / total_days) * 100)

    def generate_next_session_name(self):
        year = self.academic_year
        session = self.semester
        year_match = re.search(r'(\d{4})/(\d{4})', year)
        start_date = self.start_date + datetime.timedelta(days=1)
        current_sem = int(session)

        if current_sem < len(self.SEMESTER_CHOICES):
            next_sem = current_sem + 1
            next_year_string = year
        else:
            next_sem = 1
            if year_match:
                start_yr = int(year_match.group(1)) + 1
                end_year = int(year_match.group(2)) + 1
                next_year_string = f"{start_yr}/{end_year}"
            else:
                next_year_string = " "

        return (next_sem, start_date, next_year_string)

    @classmethod
    def rollover_academic_session(cls, keep_professor=True):
        from .curriculum import Curriculum

        with transaction.atomic():
            current_session = cls.objects.get(is_active=True)
            next_sem, start_date, next_year = current_session.generate_next_session_name()

            next_session, created = cls.objects.get_or_create(
                academic_year=next_year,
                semester=next_sem,
                is_active=True,
                start_date=start_date
            )

            session_prev = cls.objects.get(
                semester=next_sem,
                academic_year=current_session.academic_year
            )

            cloned_count = Curriculum.clone_curriculum(
                from_session_id=session_prev.record_id,
                to_session_id=next_session.record_id
            )

            current_session.is_active = False
            current_session.save()
            next_session.is_active = True
            next_session.save()

            return next_session, cloned_count


class Course(BaseModelMixin):
    """
    Unified University Course Registry. Accommodates Undergraduate, 
    Practical-heavy, Experiential, and Postgraduate Research modules.
    """

    type_choices = [
        ("C",  "Core"),
        ("E",  "Elective"),
        ("CC", "Common Unit"),
        ("P", "Practical / Laboratory Unit"),
        ("IA", "Industrial Attachment / Internship"),
        ("TP", "Teaching Practice / Field Practicum"),
        ("PR", "Postgraduate Research Thesis / Dissertation"),
        ("ST", "Specialised Seminar / Independent Study"),
    ]

    course_name = models.CharField(max_length=255)
    course_code = models.CharField(
        unique=True,
        max_length=74,
        help_text="e.g., CCS 401, BIL 810"
    )

    department = models.ForeignKey('Department', on_delete=models.PROTECT)

    course_type = models.CharField(
        choices=type_choices,
        default='C',
        max_length=45,
        db_index=True
    )

    # 2. Base Credit Representation (CUE: 1 Credit = 15 Instructional Hours)
    credits = models.IntegerField(
        default=3,
        help_text="Undergraduate units default to 3 credits. PhD Research can scale up to 15+ credits."
    )

    # 3. Mode Hours Tracking (Required for CUE Curriculum Audits)
    lecture_hours_per_week = models.PositiveIntegerField(default=3)
    practical_hours_per_week = models.PositiveIntegerField(
        default=0,
        help_text="Required if course_type is P (Practical/Lab)."
    )

    # 4. Industrial Attachment & Field Experiential Metrics
    attachment_duration_weeks = models.PositiveIntegerField(
        default=0,
        help_text="Mandatory weeks for industrial attach/practicums. Usually 8-12 weeks under CUE guidelines."
    )
    is_externally_assessed = models.BooleanField(
        default=False,
        help_text="Requires an appointed external university assessor/supervisor field-visit grade signoff."
    )

    # 5. Specialized Postgraduate Research Vectors (Masters / PhDs)
    is_postgraduate_only = models.BooleanField(
        default=False,
        help_text="Hard lock variable preventing undergraduate students from registering into this code."
    )
    requires_defense_panel = models.BooleanField(
        default=False,
        help_text="Mandatory for Thesis/Dissertation options. Triggers Senate Board of Examiners appointment workflows."
    )

    expected_competencies = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="List of core skill competencies mapped to this course for UCBEF checks."
    )

    prerequisites = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
    )

    unesco_isced = models.CharField(
        max_length=123,
        null=True,
        choices=UNESCO_ISCED_FIELDS,
        blank=True,
        help_text="Standardized UNESCO tag for this specific subject matter."
    )

    offered = models.IntegerField(
        default=1,
        help_text="Year of study this unit is typically scheduled."
    )

    class Meta:
        verbose_name = "Course Module"
        verbose_name_plural = "Course Modules"

    def clean(self):
        """
        Structural Integrity Middleware: Enforces CUE operational parameters across 
        distinct academic unit styles.
        """
        super().clean()

        # Rule A: Industrial Attachment Guardrails
        if self.course_type == 'IA':
            if self.attachment_duration_weeks == 0:
                raise ValidationError({
                    'attachment_duration_weeks': "CUE Academic Guidelines require a defined duration (in weeks) "
                    "for all active Industrial Attachment / Internship models."
                })
            self.lecture_hours_per_week = 0
            self.practical_hours_per_week = 0

        # Rule B: Postgraduate Research (Thesis/Dissertation) Core Controls
        if self.course_type == 'PR':
            self.is_postgraduate_only = True
            self.requires_defense_panel = True
            self.lecture_hours_per_week = 0
            self.practical_hours_per_week = 0

            if self.credits < 6:
                raise ValidationError({
                    'credits': "CUE Thesis Weighting Rule: Postgraduate Research projects must carry substantial credit "
                               "load structures (Minimum 6 credits for Masters, significantly higher for Doctorates)."
                })

        # Rule C: Practical Lab Class Hour Alignments
        if self.course_type == 'P' and self.practical_hours_per_week == 0:
            raise ValidationError({
                'practical_hours_per_week': "Practical/Laboratory course types require assigning continuous weekly lab hours."
            })

    def __str__(self):
        return f"{self.course_code} — {self.course_name} ({self.get_course_type_display()})"
