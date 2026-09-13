import datetime
import random
from datetime import date
from django.contrib.auth import get_user_model
import factory
from factory.django import DjangoModelFactory

from base.models import Student, Tclass, Programme, School, Department, Session
from base.models.student.reference import KENYAN_COUNTIES

User = get_user_model()

# ----------------------------------------------------
# 1. CORE OPERATIONAL SESSION FACTORY
# ----------------------------------------------------


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = Session

    # In-memory tracking state variables
    _current_year = 2025
    _current_trimester = 0

    @classmethod
    def _advance_trimester_timeline(cls):
        """Advances the trimester cycle and increments calendar years sequentially"""
        cls._current_trimester += 1
        if cls._current_trimester > 3:
            cls._current_trimester = 1
            cls._current_year += 1

    @factory.lazy_attribute
    def academic_year(self):
        SessionFactory._advance_trimester_timeline()
        next_year = SessionFactory._current_year + 1
        return f"{SessionFactory._current_year}/{next_year}"

    @factory.lazy_attribute
    def semester(self):
        return str(SessionFactory._current_trimester)

    @factory.lazy_attribute
    def start_date(self):
        year = SessionFactory._current_year
        if SessionFactory._current_trimester == 1:
            return date(year, 9, 1)
        elif SessionFactory._current_trimester == 2:
            return date(year + 1, 1, 1)
        else:
            return date(year + 1, 5, 1)

    @factory.lazy_attribute
    def end_date(self):
        year = SessionFactory._current_year
        if SessionFactory._current_trimester == 1:
            return date(year, 12, 31)
        elif SessionFactory._current_trimester == 2:
            return date(year + 1, 4, 30)
        else:
            return date(year + 1, 8, 31)

    @factory.lazy_attribute
    def is_active(self):
        return False

    @factory.post_generation
    def set_only_latest_active(obj, create, extracted, **kwargs):
        if not create:
            return
        Session.objects.exclude(id=obj.id).update(is_active=False)
        obj.is_active = True
        obj.save()


# ----------------------------------------------------
# 2. HIERARCHICAL INFRASTRUCTURE FACTORIES
# ----------------------------------------------------

class SchoolFactory(DjangoModelFactory):
    class Meta:
        model = School

    school_name = factory.Iterator([
        'Engineering & Architecture',
        'Computing & Informatics',
        'Business & Economics',
        'Health Sciences',
        'Law & Social Sciences',
        'Pure & Applied Sciences',
    ])


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    school = factory.SubFactory(SchoolFactory)

    @factory.lazy_attribute
    def department_name(self):
        mapping = {
            'Engineering & Architecture': [
                'Civil Engineering',
                'Mechanical Engineering',
                'Electrical Engineering'
            ],
            'Computing & Informatics': [
                'Computer Science',
                'Information Technology',
                'Software Engineering'
            ],
            'Business & Economics': [
                'Accounting & Finance',
                'Business Administration',
                'Economics'
            ],
            'Health Sciences': [
                'Nursing',
                'Public Health',
                'Clinical Medicine'
            ],
            'Law & Social Sciences': [
                'Law',
                'Sociology',
                'Psychology'
            ],
            'Pure & Applied Sciences': [
                'Mathematics',
                'Physics',
                'Chemistry',
                'Biology'
            ]
        }

        school_name = self.school.school_name

        if school_name in mapping:
            return random.choice(mapping[school_name])

        return "General Studies"


# ----------------------------------------------------
# 3. ACADEMIC PROGRAMME & GROUP TRACKING FACTORIES
# ----------------------------------------------------

# Mappings defined as module-level constants
CODE_MAPPING = {
    # Computing & Informatics
    'Computer Science': 'COM',
    'Information Technology': 'BIT',
    'Software Engineering': 'SWE',
    'Business Information Technology': 'BBIT',

    # Engineering
    'Civil Engineering': 'CIV',
    'Mechanical Engineering': 'MEC',
    'Electrical Engineering': 'EEE',
    'Engineering': 'BENG',

    # Business
    'Accounting & Finance': 'ACC',
    'Business Administration': 'BBA',
    'Economics': 'ECO',
    'Finance': 'FIN',

    # Health Sciences
    'Nursing': 'NUR',
    'Public Health': 'BPH',
    'Clinical Medicine': 'CLM',

    # Law & Social Sciences
    'Law': 'LLB',
    'Sociology': 'SOC',
    'Psychology': 'PSY',

    # Pure & Applied Sciences
    'Mathematics': 'MATH',
    'Physics': 'PHY',
    'Chemistry': 'CHEM',
    'Biology': 'BIO',

    # Postgraduate
    'Master of Science': 'MSC',
    'Master of Business Administration': 'MBA',
    'Master of Public Health': 'MPH',
    'Master of Arts': 'MA',
    'Master of Laws': 'LLM',
    'Master of Education': 'MED',

    # Doctoral
    'Doctor of Philosophy': 'PhD',
    'Doctor of Medicine': 'MD',

    # Other
    'Education': 'BED',
    'Arts': 'BA',
    'General Studies': 'GEN',
}

DEGREE_TYPE_MAPPING = {
    # Undergraduate Degrees
    'Bachelor of Science': 'BSc',
    'Bachelor of Science in Computer Science': 'BSc',
    'Bachelor of Science in Information Technology': 'BSc',
    'Bachelor of Science in Software Engineering': 'BSc',
    'Bachelor of Science in Civil Engineering': 'BSc',
    'Bachelor of Science in Mechanical Engineering': 'BSc',
    'Bachelor of Science in Electrical & Electronic Engineering': 'BSc',
    'Bachelor of Science in Finance': 'BSc',
    'Bachelor of Science in Economics & Statistics': 'BSc',
    'Bachelor of Science in Nursing': 'BSc',
    'Bachelor of Science in Public Health': 'BSc',
    'Bachelor of Science in Clinical Medicine': 'BSc',
    'Bachelor of Science in Mathematics': 'BSc',
    'Bachelor of Science in Physics': 'BSc',
    'Bachelor of Science in Chemistry': 'BSc',
    'Bachelor of Science in Biology': 'BSc',
    'Bachelor of Commerce': 'BCom',
    'Bachelor of Commerce (Accounting Option)': 'BCom',
    'Bachelor of Business Administration': 'BCom',
    'Bachelor of Business Information Technology': 'BBIT',
    'Bachelor of Laws': 'LLB',
    'Bachelor of Education': 'BEd',
    'Bachelor of Arts': 'BA',
    'Bachelor of Arts in General Studies': 'BA',
    'Bachelor of Engineering': 'BEng',
    'Bachelor of Technology in Mechanical Systems': 'BEng',
    'Bachelor of Nursing': 'BSc',

    # Postgraduate Degrees
    'Master of Science': 'MSc',
    'Master of Science in Computer Science': 'MSc',
    'Master of Business Administration': 'MBA',
    'Master of Public Health': 'MPH',
    'Master of Arts': 'MA',
    'Master of Laws': 'LLM',
    'Master of Education': 'MEd',

    # Doctoral Degrees
    'Doctor of Philosophy': 'PhD',
    'Doctor of Medicine': 'MD',

    # Diplomas
    'Diploma in Civil Engineering': 'PGDE',
    'Diploma in Electrical Engineering': 'PGDE',
    'Diploma in Engineering': 'PGDE',
    'Diploma in Computer Science': 'PGDE',
    'Diploma in Information Technology': 'PGDE',
    'Diploma in Business Administration': 'PGDE',
    'Diploma in Nursing': 'PGDE',
}

PROGRAMME_NAME_MAPPING = {
    # Computing & Informatics
    'Computer Science': [
        'Bachelor of Science in Computer Science',
        'Master of Science in Computer Science'
    ],
    'Information Technology': [
        'Bachelor of Science in Information Technology',
        'Bachelor of Business Information Technology'
    ],
    'Software Engineering': [
        'Bachelor of Science in Software Engineering'
    ],

    # Engineering
    'Civil Engineering': [
        'Bachelor of Science in Civil Engineering',
        'Diploma in Civil Engineering'
    ],
    'Mechanical Engineering': [
        'Bachelor of Science in Mechanical Engineering',
        'Bachelor of Technology in Mechanical Systems'
    ],
    'Electrical Engineering': [
        'Bachelor of Science in Electrical & Electronic Engineering',
        'Diploma in Electrical Engineering'
    ],

    # Business
    'Accounting & Finance': [
        'Bachelor of Commerce (Accounting Option)',
        'Bachelor of Science in Finance'
    ],
    'Business Administration': [
        'Bachelor of Business Administration',
        'Master of Business Administration (MBA)'
    ],
    'Economics': [
        'Bachelor of Science in Economics & Statistics',
        'Bachelor of Arts'
    ],
    'Finance': [
        'Bachelor of Science in Finance'
    ],

    # Health Sciences
    'Nursing': [
        'Bachelor of Science in Nursing'
    ],
    'Public Health': [
        'Bachelor of Science in Public Health',
        'Master of Public Health'
    ],
    'Clinical Medicine': [
        'Bachelor of Science in Clinical Medicine'
    ],

    # Law & Social Sciences
    'Law': [
        'Bachelor of Laws',
        'Master of Laws'
    ],
    'Sociology': [
        'Bachelor of Arts in Sociology',
        'Master of Arts in Sociology'
    ],
    'Psychology': [
        'Bachelor of Arts in Psychology',
        'Master of Arts in Psychology'
    ],

    # Pure & Applied Sciences
    'Mathematics': [
        'Bachelor of Science in Mathematics',
        'Master of Science in Mathematics'
    ],
    'Physics': [
        'Bachelor of Science in Physics',
        'Master of Science in Physics'
    ],
    'Chemistry': [
        'Bachelor of Science in Chemistry',
        'Master of Science in Chemistry'
    ],
    'Biology': [
        'Bachelor of Science in Biology',
        'Master of Science in Biology'
    ],

    # General
    'General Studies': [
        'Bachelor of Arts in General Studies'
    ],
}


class ProgrammeFactory(DjangoModelFactory):
    class Meta:
        model = Programme

    department = factory.SubFactory(DepartmentFactory)

    @factory.lazy_attribute
    def programme_name(self):
        dept_name = self.department.department_name

        if dept_name in PROGRAMME_NAME_MAPPING:
            return random.choice(PROGRAMME_NAME_MAPPING[dept_name])

        return "Bachelor of Arts in General Studies"

    @factory.lazy_attribute
    def code(self):
        """Generate programme code from the programme name"""
        prog_name = self.programme_name

        # Try to find a code by matching department name first
        dept_name = self.department.department_name
        if dept_name in CODE_MAPPING:
            return CODE_MAPPING[dept_name]

        # Then try to match by programme name keywords
        for key, code in CODE_MAPPING.items():
            if key in prog_name:
                return code

        return 'GEN'

    @factory.lazy_attribute
    def degree_type(self):
        prog_name = self.programme_name

        # Try exact match first
        if prog_name in DEGREE_TYPE_MAPPING:
            return DEGREE_TYPE_MAPPING[prog_name]

        # Try partial match - look for degree type in the programme name
        for degree_name, degree_code in DEGREE_TYPE_MAPPING.items():
            if degree_name in prog_name:
                return degree_code

        # Default fallback
        return 'BSc'

    @factory.lazy_attribute
    def level(self):
        """Determine level based on programme name"""
        prog_name = self.programme_name
        if 'Master' in prog_name or 'MBA' in prog_name:
            return 'Postgraduate'
        elif 'Doctor' in prog_name or 'PhD' in prog_name:
            return 'Postgraduate'
        elif 'Diploma' in prog_name:
            return 'Diploma'
        elif 'Certificate' in prog_name:
            return 'Certificate'
        else:
            return 'Undergraduate'

    @factory.lazy_attribute
    def status(self):
        return 'Active'

    @factory.lazy_attribute
    def capacity(self):
        return 70

    @factory.lazy_attribute
    def duration_years(self):
        prog_name = self.programme_name
        if 'Master' in prog_name or 'MBA' in prog_name:
            return 2
        elif 'Doctor' in prog_name or 'PhD' in prog_name:
            return 4
        elif 'Diploma' in prog_name:
            return 2
        elif 'Certificate' in prog_name:
            return 1
        else:
            return 4

    @factory.lazy_attribute
    def semesters_per_year(self):
        return 2

    @factory.lazy_attribute
    def total_credits_required(self):
        if self.duration_years == 4:
            return 120
        elif self.duration_years == 2:
            return 60
        else:
            return 30

    @factory.lazy_attribute
    def description(self):
        return f"Comprehensive programme in {self.programme_name}"

    kuccps_programme_code = factory.Sequence(lambda n: f"{1279115 + n}")
    current_class = None
    unesco_isced = None


class TclassFactory(DjangoModelFactory):
    class Meta:
        model = Tclass

    programme = factory.SubFactory(ProgrammeFactory)

    # Track created class identifiers in-memory to prevent duplicates
    _created_classes = set()

    @factory.lazy_attribute
    def class_name(self):
        # Use the programme code directly from the programme
        prefix = self.programme.code

        # Get the short 2-digit format of the current year
        current_year_short = datetime.datetime.now().strftime('%y')

        # Track and generate unique cohorts using a suffix loop
        suffix = 1
        while True:
            if suffix == 1:
                potential_name = f"{prefix}/{current_year_short}"
            else:
                stream_letter = chr(63 + suffix)
                potential_name = f"{prefix}/{current_year_short}-{stream_letter}"

            if potential_name not in TclassFactory._created_classes:
                TclassFactory._created_classes.add(potential_name)
                return potential_name

            suffix += 1

    year_of_study = 1
    graduated = None
    liason = None


# ----------------------------------------------------
# 4. IDENTITY & CORE STUDENT DOMAIN FACTORIES
# ----------------------------------------------------

class StudentUserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name', locale='en_KE')
    last_name = factory.Faker('last_name', locale='en_KE')
    surname = factory.Faker('last_name', locale='en_KE')
    gender = factory.Iterator(['male', 'female'])
    is_active = True
    is_staff = False
    is_activated = True

    @factory.lazy_attribute
    def email(self):
        rand_num = random.randint(100, 999)
        return f"{self.first_name.lower()}.{self.surname.lower()}.{rand_num}@email.com"

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password_to_set = extracted or 'testpass123'
        self.set_password(password_to_set)
        if create:
            self.save()


class StudentFactory(DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(StudentUserFactory)
    class_entered = factory.SubFactory(TclassFactory)
    current_class = factory.SelfAttribute('class_entered')

    # Registration number counter
    _registration_counter = 0

    @factory.lazy_attribute
    def registration_number(self):
        # Use the programme code from the associated programme
        prog = self.class_entered.programme.code.upper().strip()
        short_yr = f"{datetime.datetime.now():%y}"
        StudentFactory._registration_counter += 1
        return f"{prog}/{StudentFactory._registration_counter:04d}/{short_yr}"

    @factory.lazy_attribute
    def school_email(self):
        return f"{self.registration_number.replace('/', '').lower()}@inst.com"

    # --- Choice Fields & Baseline Data Fields ---
    admission_pathway = 'KUCCPS'
    marital_status = 'U'
    id_type = 'national'
    national_id = factory.Sequence(lambda n: f"{12345678 + n}")

    religion = 'Christian'
    nationality = 'Kenyan'
    ethnicity = factory.Iterator(
        ['Kikuyu', 'Luo', 'Luhya', 'Kalenjin', 'Kamba'])
    date_of_birth = datetime.date(2005, 1, 1)
    place_of_birth = factory.Faker('city', locale='en_KE')
    telephone_no = factory.Sequence(lambda n: f"0712345{n:03d}")

    domicile = 'kenya'
    county = factory.Iterator(
        [c[0] if isinstance(c, tuple) else c for c in KENYAN_COUNTIES])
    home_address = factory.Faker('address', locale='en_KE')

    kcse_mean_grade = 'B-plain'
    disabled = False
    disability_status = "None"
    stay = 'resident'
    name_of_secondary_school = factory.LazyAttribute(
        lambda o: f"{o.user.surname} High School"
    )
    address_of_secondary_school = factory.Faker('address', locale='en_KE')
