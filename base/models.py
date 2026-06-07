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

import uuid
import re
import datetime


from django.db import (
    models,
    DatabaseError,
    transaction
)
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError

from .managers import CommonUnitCurriculumManager, DeferredStudentManager, GraduatedStudentManager, ResidentStudentManager, UserManager

from simple_history.models import HistoricalRecords

GENDER_CHOICES = [
    ("M", "Male"),
    ("F", "Female"),
]


class TimeStampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModelMixin(
    TimeStampedMixin,
    models.Model
):
    record_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True


class hasUserMixin(models.Model):
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='%(class)s_profile'
    )

    class Meta:
        abstract = True


class HasClassMixin(models.Model):
    tclass = models.ForeignKey(
        'TClass',
        on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True
    pass


class WithDepartmentMixin(models.Model):
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='%(class)s_set'
    )

    class Meta:
        abstract = True


class WithSchoolMixin(models.Model):
    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        related_name='%(class)s_set'
    )

    class Meta:
        abstract = True


class StaffUserMixin(
    hasUserMixin,
    models.Model
):
    staff_number = models.CharField(max_length=20, unique=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.staff_number} - {self.user}"

    def save(self, *args, **kwargs):
        self.user.is_staff = True
        self.user.save()
        super().save(*args, **kwargs)


class WithClassMixin(models.Model):
    Tclass = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


class Institution(BaseModelMixin):
    active_session = models.ForeignKey(
        'Session',
        on_delete=models.DO_NOTHING
    )

    institution_name = models.CharField(max_length=123)
    logo = models.ImageField(upload_to='logo/')

    class Meta:
        abstract = True


class School(BaseModelMixin):

    school_name = models.CharField(max_length=78)

    active_session = models.ForeignKey(
        "Session",
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"school of {self.school_name} "


class Department(
    WithSchoolMixin,
    BaseModelMixin
):

    department_name = models.CharField(max_length=123)

    def __str__(self):
        return f"Department of {self.department_name} "


class Programme(
    BaseModelMixin,
    WithDepartmentMixin
):
    kenyan_degrees = [
        # Bachelor's Degrees (Undergraduate)
        ("BSc", "Bachelor of Science"),
        ("BEd", "Bachelor of Education"),
        ("LLB", "Bachelor of Laws"),
        ("BA", "Bachelor of Arts"),
        ("BCom", "Bachelor of Commerce"),
        ("BBIT", "Bachelor of Business Information Technology"),
        ("B.Arch", "Bachelor of Architecture"),
        ("BEng", "Bachelor of Engineering"),
        ("MBChB", "Bachelor of Medicine and Bachelor of Surgery"),
        ("BPharm", "Bachelor of Pharmacy"),
        ("BDS", "Bachelor of Dental Surgery"),

        # Post-Graduate Diplomas
        ("PGDE", "Post Graduate Diploma in Education"),

        # Master's Degrees (Postgraduate)
        ("MSc", "Master of Science"),
        ("MA", "Master of Arts"),
        ("MBA", "Master of Business Administration"),
        ("LLM", "Master of Laws"),
        ("MEd", "Master of Education"),
        ("MPH", "Master of Public Health"),

        # Doctorate Degrees (Terminal)
        ("PhD", "Doctor of Philosophy"),
        ("MD", "Doctor of Medicine")
    ]

    degree_type = models.CharField(
        max_length=123,
        choices=kenyan_degrees
    )

    programme_name = models.CharField(max_length=100)
    # TODO : should be foreign key relationship ✔️

    current_class = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT,
        related_name='current_class',
        null=True,
        blank=True
    )

    duration_years = models.IntegerField(default=4)
    semesters_per_year = models.IntegerField(default=2)

    @property
    def total_semesters(self):
        return self.duration_years * self.semesters_per_year

    # TODO : add the type i.e bsc,llb,BA field enum✔️

    def __str__(self):
        return f"{self.programme_name} "


class Tclass(BaseModelMixin):
    class_name = models.CharField(max_length=78)

    programme = models.ForeignKey(
        "Programme",
        models.PROTECT
    )

    courses = models.ManyToManyField(
        'Course', through='Curriculum'
    )

    # TODO : year of study to be here  remove from student records✔️

    # TODO : make this dynamic on reporting /results
    # TODO : cap max years
    # TODO : make sure two classes cant have the same year of study
    year_of_study = models.IntegerField(
        default=1,
        null=True,
        blank=True,
    )

    # authoritative date for the entire class
    graduated = models.DateField(null=True)
    # TODO : remove the above two from student ✔️

    def __str__(self):
        return f"{self.class_name}"


class Hostel(BaseModelMixin):
    """
    A physical hostel building on campus.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('mixed', 'Mixed'),
    ]

    name = models.CharField(max_length=78)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        related_name='hostels'
    )
    warden = models.ForeignKey(
        'HostelWarden',  # or User
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_hostels'
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def total_capacity(self):
        return self.rooms.aggregate(
            total=models.Sum('capacity')
        )['total'] or 0

    @property
    def occupied_beds(self):
        return HostelAllocation.objects.filter(
            room__hostel=self,
            is_active=True
        ).count()

    @property
    def available_beds(self):
        return self.total_capacity - self.occupied_beds


class Room(BaseModelMixin):
    """
    An individual room within a hostel.
    """
    ROOM_TYPE_CHOICES = [
        ('single',  'Single'),
        ('double',  'Double'),
        ('triple',  'Triple'),
        ('ensuite', 'En-suite'),
    ]

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.PROTECT,
        related_name='rooms'
    )
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES)
    capacity = models.IntegerField(default=2)
    floor = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('hostel', 'room_number')

    def __str__(self):
        return f"{self.hostel.name} — Room {self.room_number}"

    @property
    def is_full(self):
        return HostelAllocation.objects.filter(
            room=self, is_active=True
        ).count() >= self.capacity

    @property
    def occupants(self):
        return HostelAllocation.objects.filter(
            room=self, is_active=True
        ).select_related('student__user')


class HostelAllocation(BaseModelMixin):
    """
    Links a student to a specific room for a specific session.
    Replaces student.hostel CharField.
    """
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='hostel_allocations'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='allocations'
    )
    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='hostel_allocations'
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        # one room slot per student per session
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student} → {self.room} ({self.session})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.room.is_full:
            raise ValidationError(
                f"Room {self.room} is at full capacity."
            )
        # gender check
        student_gender = self.student.user.gender
        hostel_gender = self.room.hostel.gender
        if hostel_gender != 'mixed' and student_gender != hostel_gender:
            raise ValidationError(
                f"{self.room.hostel.name} does not accommodate {student_gender} students."
            )

# --- Users ---


class User(
    BaseModelMixin,
    AbstractBaseUser,
    PermissionsMixin
):

    STUDENT = 'student'
    STAFF = 'staff'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (STAFF, 'Staff'),
        (ADMIN, 'Admin'),
    ]

    first_name = models.CharField(
        max_length=78,
        null=True
    )

    last_name = models.CharField(
        max_length=78,
        null=True
    )

    surname = models.CharField(
        max_length=78,
        null=True
    )

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES
    )

    profile_picture = models.ImageField(
        null=True,
        blank=True,
        upload_to='profiles/',
        default='profiles/profile.jpg'
    )

    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    is_activated = models.BooleanField(default=False)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        'first_name',
        'last_name'
    ]

    objects = UserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname or " "} {self.last_name}"

    @property
    def half_name(self):
        return f"{self.first_name}  {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}"


id_type_choices = [
    ('national', 'national Id'),
    ('passport', 'passport'),
    ('birthCert', 'Birth Certificate')
]


class Student(
    BaseModelMixin,
    hasUserMixin
):

    MARRIAGE_STATUS = [
        ("M", "Married"),
        ("U", "Unmarried")
    ]

    stay_choices = [
        ('resident', 'Resident'),
        ('outside', 'Outside')
    ]

    # personal info

    marital_status = models.CharField(
        max_length=20,
        choices=MARRIAGE_STATUS,
        default="U"
    )

    name_of_spouse = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    spouse_contact = models.CharField(
        max_length=19,
        null=True,
        blank=True
    )

    occupation_of_spouse = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    number_of_children = models.IntegerField(
        null=True,
        blank=True
    )

    # TODO : have type i.e id | passport | birth cert , json field maybe ✔️
    # TODO : make Unique ✔️

    id_type = models.CharField(
        max_length=24,
        default='national',
        choices=id_type_choices
    )

    national_id = models.CharField(
        max_length=34,
        default="xxxxxxx",
        unique=True
    )

    religion = models.CharField(
        max_length=34,
        default='pagan'
    )

    nationality = models.CharField(
        max_length=34,
        default='Kenyan'
    )

    ethnicity = models.CharField(
        max_length=34,
        default=' '
    )

    date_of_birth = models.DateField(
        default=datetime.date(2000, 4, 12)
    )

    place_of_birth = models.CharField(
        max_length=255,
        default=''
    )

    telephone_no = models.CharField(
        max_length=78,
        default='07xxxxx'
    )

    school_email = models.EmailField(
        default='example@inst.com',
        unique=True
    )

    domicile = models.CharField(
        max_length=78,
        default='kenya'
    )

    county = models.CharField(
        max_length=78,
        default='kenya'
    )

    sub_county = models.CharField(
        max_length=78,
        default='kenya'
    )

    constituency = models.CharField(
        max_length=78,
        default='kenya'
    )

    division = models.CharField(
        max_length=78,
        default=''
    )

    location = models.CharField(
        max_length=78,
        default='kenya'
    )

    home_adress = models.CharField(
        max_length=78,
        default='kenya'
    )  # TODO : correct type address

    # educational Info
    registration_number = models.CharField(
        max_length=78,
        default='programme/000/2X',
        unique=True
    )

    class_entered = models.ForeignKey(
        to=Tclass,
        on_delete=models.PROTECT
    )  # to replaced by foreign key Relationship ✔️

    stay = models.CharField(
        max_length=78,
        default='resident',
        choices=stay_choices
    )  # to be enum resident,outside ✔️

    # hostel_choices = [
    #     ('a', "A"),
    #     ('b', 'B'),
    #     ('c', 'C')
    # ]

    # hostel = models.CharField(
    #     max_length=78,
    #     blank=True,
    #     null=True,
    #     choices=hostel_choices
    # )  # TODO : make its own model i.e hostel model and room model

    enrolled = models.DateTimeField(
        auto_now_add=True
    )  # TODO : make this reporting day

    deferred = models.BooleanField(
        default=False
    )

    name_of_secondary_school = models.CharField(
        max_length=78,
    )

    address_of_secondary_school = models.CharField(
        max_length=255
    )

    enrollments = models.ManyToManyField(
        'Curriculum',
        related_name='enrolled_students',
        through='Enrollment',
        blank=True
    )  # TODO : add through for enrollment status tracking ✔️

    def __str__(self):
        return self.registration_number

    @property
    def expected_graduation_session(self):
        """
        Returns the expected graduation Session based on:
        - Programme duration (default 4 years = 8 semesters)
        - Number of active/completed deferments
        - Enrolment session
        """

        PROGRAMME_SEMESTERS = 8  # make this dynamic per programme later

        # count semesters deferred (each deferment = 1 semester lost)
        deferred_count = self.deferments.exclude(
            status='withdrawn'  # withdrawn students handled separately
        ).count()

        total_semesters = PROGRAMME_SEMESTERS + deferred_count

        # find which session they enrolled in
        try:
            # get all sessions ordered chronologically
            all_sessions = list(
                Session.objects.order_by(
                    'academic_year', 'semester'
                ).values('record_id', 'academic_year', 'semester')
            )

            # find their enrollment session
            enrollment_session = Session.objects.filter(
                curriculum__enrollment_records__student=self,
            ).order_by('academic_year', 'semester').first()

            if not enrollment_session:
                return None

            # find index of enrollment session
            start_idx = next(
                (i for i, s in enumerate(all_sessions)
                 if str(s['record_id']) == str(enrollment_session.record_id)),
                None
            )

            if start_idx is None:
                return None

            # expected graduation is total_semesters ahead
            grad_idx = start_idx + total_semesters - 1
            if grad_idx >= len(all_sessions):
                return None  # not enough sessions created yet

            grad_session_id = all_sessions[grad_idx]['record_id']
            return Session.objects.get(record_id=grad_session_id)

        except Exception:
            return None

    @property
    def semesters_remaining(self):
        """How many semesters until expected graduation"""

        expected = self.expected_graduation_session
        current = Session.objects.filter(is_active=True).first()

        if not expected or not current:
            return None

        all_sessions = list(
            Session.objects.order_by(
                'academic_year', 'semester'
            ).values_list('record_id', flat=True)
        )

        try:
            current_idx = [str(s)
                           for s in all_sessions].index(str(current.record_id))
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
        from .models import Session
        session = Session.objects.filter(is_active=True).first()
        if not session:
            return None
        allocation = self.hostel_allocations.filter(
            session=session, is_active=True
        ).select_related('room__hostel').first()
        return allocation.room if allocation else None


class DeferredStudent(Student):
    """Same table, different admin view"""

# What you can and can't do with proxy models
# You can:

# Add Python methods and properties
# Define a different default ordering
# Register a separate ModelAdmin with different display/filters
# Override the manager to always filter a subset

# You can't:
# Add new database fields
# Have a separate table

    objects = DeferredStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Deferred Students'

    def reinstate(self):
        """bring a deferred student back"""
        self.deferred = False
        self.save()

    @property
    def days_deferred(self):
        from django.utils import timezone
        return (timezone.now().date() - self.updated_at.date()).days


class ResidentStudent(Student):
    """Same table, filtered to residents only"""
    objects = ResidentStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Resident Students'


class GraduatedStudent(Student):
    objects = GraduatedStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Graduated Students'


class ParentGuardian(BaseModelMixin):
    RELATION_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='parents'
    )
    relation = models.CharField(
        max_length=20,
        choices=RELATION_CHOICES
    )
    name = models.CharField(max_length=255)
    id_type = models.CharField(
        max_length=24,
        choices=id_type_choices
    )

    id_no = models.CharField(max_length=34)
    date_of_birth = models.DateField()


class EmergencyContact(BaseModelMixin):
    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    name = models.CharField(max_length=78)
    phone = models.CharField(max_length=78)
    email = models.CharField(max_length=78)
    relationship = models.CharField(max_length=78)
    address = models.CharField(max_length=78, null=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        # one primary contact per student
        unique_together = ('student', 'is_primary')


class Lecturer(
    WithDepartmentMixin,
    StaffUserMixin,
    BaseModelMixin
):

    academic_titles = [
        # Graduate & Early Career Roles
        ("Graduate Assistant", "Graduate Assistant"),
        ("Teaching Assistant", "TA"),
        ("Tutorial Fellow", "Tutorial Fellow"),

        # Standard Lecturer Ranks
        ("Junior Lecturer", "Junior Lecturer"),
        ("Lecturer", "Lecturer"),
        ("Senior Lecturer", "Senior Lecturer"),

        # Advanced / Professorial Ranks
        ("Associate Professor", "Associate Professor"),
        ("Professor", "Professor"),
        ("Full Professor", "Full Professor"),
        ("Distinguished Professor", "Distinguished Professor"),
        ("Emeritus Professor", "Professor Emeritus"),

        # Adjunct & Part-Time Roles
        ("Adjunct Lecturer", "Adjunct Lecturer"),
        ("Visiting Lecturer", "Visiting Lecturer"),
        ("Guest Lecturer", "Guest Lecturer"),
        ("Part-Time Lecturer", "Part-Time Lecturer"),

        # Institutional & Departmental Leadership Roles
        ("Head of Department", "HOD"),
        ("Dean of Faculty", "Dean"),
        ("Director of School", "Director"),
        ("Chaired Professor", "Endowed Chair")
    ]

    academic_titles_abbreviated = [
        # Graduate & Early Career Roles
        ("Graduate Assistant", "GA"),
        ("Teaching Assistant", "TA"),
        ("Tutorial Fellow", "TF"),
        ("Assistant Lecturer", "Asst. Lec."),

        # Standard Lecturer Ranks
        ("Junior Lecturer", "Jr. Lec."),
        ("Lecturer", "Lec."),
        ("Senior Lecturer", "Snr. Lec."),

        # Advanced / Professorial Ranks
        ("Associate Professor", "Assoc. Prof."),
        ("Professor", "Prof."),
        ("Full Professor", "Full Prof."),
        ("Distinguished Professor", "Dist. Prof."),
        ("Emeritus Professor", "Prof. Emeritus"),

        # Adjunct & Part-Time Roles
        ("Adjunct Lecturer", "Adj. Lec."),
        ("Visiting Lecturer", "Vis. Lec."),
        ("Guest Lecturer", "Guest Lec."),
        ("Part-Time Lecturer", "PT Lec."),

        # Institutional & Departmental Leadership Roles
        ("Head of Department", "HOD"),
        ("Dean of Faculty", "Dean"),
        ("Director of School", "Director"),
        ("Chaired Professor", "Chair Prof.")
    ]

    # TODO : add title
    title = models.CharField(
        max_length=23,
        choices=academic_titles_abbreviated,
        default='Lecturer'
    )

    def __str__(self):
        return f"{self.staff_number} - {self.user}"


class DeptAdmin(
    BaseModelMixin,
    StaffUserMixin,
    WithDepartmentMixin
):
    pass


class SchoolAdmin(
    BaseModelMixin,
    StaffUserMixin,
    WithSchoolMixin
):
    pass


class InstitutionAdmin(
    StaffUserMixin,
    BaseModelMixin
):

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)

    #     user = self.user
    #     user.role = User.ROLE_CHOICES.ADMIN
    #     user.save()

    pass


class HostelWarden(
    StaffUserMixin,
    BaseModelMixin
):
    hostel = models.ForeignKey(
        'Hostel',
        on_delete=models.CASCADE,
        null=True,

    )


class ItStaff(
    StaffUserMixin,
    BaseModelMixin
):
    pass


class FinanceStaff(
    StaffUserMixin,
    BaseModelMixin
):
    pass

#########


class Session(BaseModelMixin):

    SEMESTER_CHOICES = [
        ("1", "Semester 1"),
        ("2", "Semester 2"),
        ("3", "Semester 3")
    ]

    academic_year = models.CharField(
        max_length=9
    )  # e.g. "2024/2025"

    semester = models.CharField(
        max_length=1,
        choices=SEMESTER_CHOICES
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True
    )

    is_active = models.BooleanField(
        default=False
    )

    @property
    def progress(self):

        today = datetime.datetime.now().date()

        # 1. Handle edge cases
        if today <= self.start_date:
            return 0
        if today >= self.end_date:
            return 100

        # 2. Calculate the days
        total_days = (self.end_date - self.start_date).days
        days_passed = (today - self.start_date).days

        # 3. Guard against division by zero if dates are identical
        if total_days <= 0:
            return 100

        # 4. Math calculation
        percentage = (days_passed / total_days) * 100
        return round(percentage)

    class Meta:
        unique_together = ('academic_year', 'semester')

    def __str__(self):
        return f"{self.academic_year} - Sem {self.semester}"

    def generate_next_session_name(self):
        year = self.academic_year
        session = self.semester
        year_match = re.search(r'(\d{4})/(\d{4})', year)
        start_date = self.start_date + datetime.timedelta(days=1)
        current_sem = int(session)

        if (current_sem < len(self.SEMESTER_CHOICES)):
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
                from_session_id=session_prev.session_id,
                to_session_id=next_session.session_id
            )

            current_session.is_active = False
            current_session.save()

            next_session.is_active = True
            next_session.save()
            return next_session, cloned_count


class Reporting(BaseModelMixin):

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='reportings',
    )

    session = models.ForeignKey(
        Session,
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


class FeeStructure(BaseModelMixin):
    """Defines what a class owes per session"""

    Tclass = models.ForeignKey(
        Tclass,
        on_delete=models.PROTECT,
        related_name='fee_structures'
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.PROTECT,
        related_name='fee_structures'
    )

    # breakdown e.g {"tuition": 45000, "registration": 5000, "hostel": 12000}
    breakdown = models.JSONField()

    @property
    def total_amount(self):
        total = 0
        for key in self.breakdown:
            total += self.breakdown[key]
        return total

    class Meta:
        unique_together = ('Tclass', 'session')

    def __str__(self):
        return f"{self.Tclass} - {self.session}"


class StudentFeeAccount(BaseModelMixin):
    """Per-student ledger for a session"""

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='fee_accounts'
    )

    fee_structure = models.ForeignKey(
        'FeeStructure',
        on_delete=models.PROTECT
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'fee_structure')

    @property
    def balance(self):
        return self.amount_billed - self.amount_paid

    @property
    def is_cleared(self):
        return self.balance <= 0

    @property
    def amount_billed(self):
        return self.fee_structure.total_amount

    @property
    def days_remaining(self):
        # Subtracts today's date from the due date

        delta = self.fee_structure.session.end_date - \
            datetime.timedelta(days=14)
        return delta

    def __str__(self):
        return f"{self.student.registration_number} - {self.fee_structure} - balance: {self.balance}"


class OverDraft(BaseModelMixin):

    account = models.ForeignKey(
        "StudentFeeAccount",
        on_delete=models.PROTECT,
        related_name='student_account'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction = models.ForeignKey(
        "Payment",
        on_delete=models.PROTECT
    )

    history = HistoricalRecords()


class Payment(BaseModelMixin):
    """Individual payment transactions"""

    STATUS_CHOICES = [
        ("pending",   "Pending"),    # initiated, awaiting confirmation
        ("completed", "Completed"),  # confirmed by webhook
        ("failed",    "Failed"),     # timed out or rejected
        ("cancelled", "Cancelled"),  # cancelled by student
    ]

    account = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='payments'
    )

    PAYMENT_METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("bank", "Bank Transfer"),
        ("cash", "Cash"),
    ]

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES
    )

    transaction_ref = models.CharField(
        max_length=100,
        unique=True,
        null=True,    # null until confirmed by webhook
        blank=True
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # provider-specific metadata
    provider_ref = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )  # MerchantRequestID, CheckoutRequestID, bank ref

    phone_number = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )  # for M-Pesa STK push

    paid_at = models.DateTimeField(auto_now_add=True)
    initiated_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('transaction_ref', 'method')

    def save(self, *args, **kwargs):
        # TODO : check if balance is cleared ✔️
        # TODO :  delete this if statement in production or make different function to create overdraft for non system payments
        if self.account.is_cleared:
            #  TODO : raise error i.e balance cleared
            return

        super().save(*args, **kwargs)

        # TODO : check for overdraft here first ✔️
        delta = self.account.balance - self.amount

        if delta < 0:
            OverDraft.objects.create(
                account=self.account,
                amount=(-delta),
                transaction=self
            )

        else:
            delta = 0

        # update amount_paid on the account
        self.account.amount_paid += (self.amount + delta)
        self.account.save()

    def confirm(self, transaction_ref, provider_ref=None):
        """
        Called by the webhook handler when payment is confirmed.
        Updates the account balance and fires notifications.
        """
        from django.utils import timezone
        from base.utils.signals import send_notification

        self.status = 'completed'
        self.transaction_ref = transaction_ref
        self.provider_ref = provider_ref
        self.paid_at = timezone.now()
        self.save()

        # update the fee account
        balance = self.account.balance
        if self.amount > balance:
            from .models import OverDraft
            OverDraft.objects.create(
                account=self.account,
                amount=self.amount - balance,
                transaction=self
            )
            self.account.amount_paid += balance
        else:
            self.account.amount_paid += self.amount
        self.account.save()

        # fire notification
        send_notification.send(
            sender=self.__class__,
            user=self.account.student.user,
            template_key='payment_confirmed',
            channels=['sms', 'email'],
            context={
                'student_name': self.account.student.user.full_name,
                'amount':       self.amount,
                'method':       self.get_method_display(),
                'ref':          self.transaction_ref,
                'balance':      self.account.balance,
                'is_cleared':   self.account.is_cleared,
            }
        )


class Course(BaseModelMixin):

    type_choices = [
        ("C", "Core"),
        ("E", "Elective"),
        ('CC', 'Common Unit')
    ]

    course_name = models.CharField(
        max_length=255
    )

    course_code = models.CharField(
        unique=True,
        max_length=74
    )

    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT
    )

    type = models.CharField(
        choices=type_choices,
        default='C',
        max_length=45
    )

    credits = models.IntegerField(
        default=3
    )

    prerequisites = models.ManyToManyField(
        "self",
        blank=True,

    )

    offered = models.IntegerField(default=1)  # year that course is offered

    # 51fdd586-2d26-4f14-b60c-7a0080ce3c0b - emmanuelbett916@gmail.com
    # 5884f293-ab08-417c-8953-fae836db3755 - com03622@uoeld.ac.ke
    def __str__(self):
        return f"{self.course_code} "


class Curriculum(BaseModelMixin):

    Tclass = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT
    )

    course = models.ForeignKey(
        'Course',
        on_delete=models.PROTECT
    )

    professor = models.ManyToManyField(
        'Lecturer',
        blank=True,
    )

    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT
    )

    results = models.ManyToManyField(
        "Student",
        through='Result'
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('course', 'Tclass', 'session')

    def __str__(self):
        return f"{self.course} - {self.session}"

    @classmethod
    def clone_curriculum(cls, from_session_id, to_session_id):
        source = cls.objects.filter(
            session_id=from_session_id).prefetch_related('professor')
        new_records = []
        professor_map = {}

        for req in source:
            obj = cls(
                course=req.course,
                Tclass=req.Tclass,
                session_id=to_session_id,
            )
            new_records.append((obj, list(req.professor.all())))

        created_objs = cls.objects.bulk_create(
            [r[0] for r in new_records],
            ignore_conflicts=True
        )

        for obj, professors in zip(created_objs, new_records):
            obj.professor.set(professors[1])

        return len(created_objs)


class CommonUnitCurriculum(Curriculum):

    objects = CommonUnitCurriculumManager()

    class Meta:
        proxy = True
        verbose_name = 'Common Unit'
        verbose_name_plural = 'Common Units'

    @property
    def classes(self):
        # find all curriculum entries for this course + session
        return Curriculum.objects.filter(
            course=self.course,
            session=self.session,
            course__type='CC'
        ).values_list('Tclass__class_name', flat=True)


class Enrollment(BaseModelMixin):

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending'
    )  # TODO : add  approved by,approved when

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'curriculum')

    def __str__(self):
        return f"{self.student} → {self.curriculum} [{self.status}]"


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
        ('active',      'Active'),       # currently deferred
        ('reinstated',  'Reinstated'),   # came back
        ('withdrawn',   'Withdrawn'),    # did not return
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
        help_text='Free text — additional context from registrar'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='approved_deferments',
        null=True
    )

    history = HistoricalRecords()

    reinstated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # can't defer twice in the same session
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"


class Result(BaseModelMixin):
    type_result = [
        ('C', 'Cat'),
        ('E', 'Exams')
    ]

    curricula = models.ForeignKey(
        'Curriculum',  # TODO : make sure only ones the student is enrolled is written
        on_delete=models.PROTECT
    )

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT
    )

    type = models.CharField(
        choices=type_result,
        default='C',
        max_length=45
    )

    score = models.DecimalField(
        decimal_places=2,
        max_digits=5
    )

    title = models.CharField(
        max_length=124
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.student} - {self.curricula} - {self.title}"


class Timetable(BaseModelMixin):

    session = models.ForeignKey(Session, on_delete=models.PROTECT)
    tclass = models.ForeignKey(Tclass, on_delete=models.PROTECT)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    lecturer = models.ForeignKey(Lecturer, on_delete=models.PROTECT)
    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100)

    class Meta:
        # prevent double-booking a venue or lecturer
        unique_together = [
            ('session', 'venue', 'day', 'start_time'),
            ('session', 'lecturer', 'day', 'start_time'),
        ]

# --- Evaluations ---


class CourseEvaluation(BaseModelMixin):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(
        default=0
    )

    comments = models.TextField(
        blank=True,
        null=True
    )


class LecturerEvaluation(
    BaseModelMixin
):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE
    )

    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(
        default=0
    )

    comments = models.TextField(
        blank=True,
        null=True
    )
