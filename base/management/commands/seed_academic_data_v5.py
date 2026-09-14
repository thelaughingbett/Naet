# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_academic_data
Usage: python manage.py seed_academic_data

Generates deterministic (replicable) seed data:
  - A dedicated system/registrar user used to approve Syllabus entries
  - 3 Schools  →  Departments  →  Courses  →  Programmes  →  Classes
  - Sessions (5, last one active: 2026/2027 Sem 1)
  - Syllabus entries (Programme × Course) — Approved for core/common units,
    Adjunct for electives — required before any class can be linked to a
    Curriculum slot for that course under that programme
  - Curriculum records keyed by (course, session) — now SHARED across every
    programme/class that teaches that course in that session, rather than
    one row per (syllabus, Tclass, session). A CurriculumClass row per
    class records which Syllabus entry authorizes that class's programme
    to attend the shared slot.
  - Lecturers assigned to curricula (via LecturerAssignment, one primary
    each) — one assignment set per shared Curriculum slot, so all classes
    attending it get the same lecturer(s), matching the new "one teaching
    slot, many classes" model.
  - FeeStructures (same year-of-study = same fees within a programme)
  - A couple of small hostels with a few rooms each
  - Students (skipping first-year students for results)
  - Results for non-first-year students (with entered_by set, and a
    workflow-appropriate `state` since Result.entered_by/state are no
    longer optional / defaulted the way they used to be)
  - StudentFeeAccounts + past payments for past sessions (continuing students)
  - A small, fixed-size set of resident students with hostel allocations
  - Prints all created user credentials, grouped by role automatically

NOTE ON THE Curriculum/CurriculumClass REFACTOR (read this first):
  Curriculum used to carry `syllabus` (FK) + `Tclass` (FK), giving one row
  per (syllabus, Tclass, session) — meaning two different programmes
  teaching "the same" course in the same session got two separate,
  unrelated Curriculum rows, each with its own lecturer assignment and
  timetable slot, even when in practice it's one shared lecture.

  Curriculum is now keyed by (course, session) directly — `course` is a
  real FK again (not a property), and WHICH classes attend it is tracked
  via a `classes` M2M through the new CurriculumClass through-table.
  CurriculumClass also records the Syllabus entry that authorizes that
  specific class's programme to attend — so per-programme approval
  (Syllabus.state) is still enforced per class, even though the teaching
  slot itself (lecturer assignment, timetable, exam session) is shared.

  Practically, for this seed command: when two programmes in the same
  department both need "CS201" in the same session, get_or_create on
  Curriculum(course=CS201, session=X) returns the SAME row the second
  time, and each programme's class gets its own CurriculumClass link
  pointing at its own Syllabus entry. Lecturer assignment then happens
  once per shared Curriculum, not once per (old) per-class row.

  This command does NOT attempt to migrate any pre-existing data seeded
  under the old shape — it assumes a fresh database. If you have old
  Curriculum rows with a `syllabus`/`Tclass` shape already in your
  database, they are incompatible with this version of the command and
  need a real data migration (mapping old per-class rows onto new
  shared-by-course rows) before rerunning seed_academic_data safely.

NOTE ON Curriculum.clone_curriculum():
  That classmethod (defined on the model, not here) still assumes the OLD
  per-class Curriculum shape (`syllabus`, `Tclass` as direct fields on
  Curriculum) and has not been updated for the course+CurriculumClass
  refactor. This command does not call clone_curriculum(), so it isn't a
  blocker here, but it WILL raise errors if invoked as-is against the new
  schema. Needs a dedicated rewrite — out of scope for this seed command.

NOTE ON RegistrationWindow:
  Enrollment.clean() requires an open RegistrationWindow for the relevant
  session/programme before an enrollment can be saved normally. This
  command still uses Enrollment.objects.bulk_create(...), which bypasses
  .save()/.clean() entirely, so seeding itself is unaffected. BUT: if you
  (or the UI) later try to manually create/approve an Enrollment against
  this seed data via .save(), it will fail until a RegistrationWindow row
  exists for that session. This command does not create RegistrationWindow
  rows because its exact field set wasn't available when this was
  written — add a small `_create_registration_windows` step once you can
  confirm its fields (term, window_type, programme, is_open/opens_at/
  closes_at, etc.).

NOTE ON Result.clean():
  As currently written, `if self.type != 'E' or self.type != 'PR':` is
  always True for any single type value (a type can never simultaneously
  equal both 'E' and 'PR'), so clean() unconditionally forces
  state='published' regardless of type. That's very likely a bug — the
  condition was probably meant to be `and`. This command does NOT rely
  on that method (bulk_create bypasses clean()) and instead sets a
  deliberately more useful `state` per type below, so the seeded dataset
  has a mix of states to exercise a results-review UI against. Worth
  fixing the `and`/`or` in the model separately.
"""

import datetime
import decimal
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# ── adjust these import paths to match your project layout ──────────────────
from base.models import (
    Course, Department, Programme, School, Session, Tclass,
    Syllabus, Curriculum, CurriculumClass, LecturerAssignment, Result,
    FeeStructure, StudentFeeAccount, Payment, Hostel, Room,
    HostelAllocation, Lecturer, Student, Enrollment
)

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Seed RNG so every run produces the same data
# ─────────────────────────────────────────────────────────────────────────────
RNG = random.Random(42)


# ─────────────────────────────────────────────────────────────────────────────
# Static data definitions
# ─────────────────────────────────────────────────────────────────────────────

SCHOOL_DATA = [
    {
        "name": "Science",
        "departments": [
            {
                "name": "Computer Science",
                "courses": [
                    ("Introduction to Programming",         "CS101", "C", 3),
                    ("Data Structures and Algorithms",      "CS201", "C", 3),
                    ("Database Management Systems",         "CS301", "C", 3),
                    ("Operating Systems",                   "CS302", "C", 3),
                    ("Computer Networks",                   "CS303", "C", 3),
                    ("Software Engineering",                "CS401", "C", 3),
                    ("Artificial Intelligence",             "CS402", "E", 3),
                    ("Machine Learning",                    "CS403", "E", 3),
                    ("Cybersecurity",                       "CS404", "E", 3),
                    ("Cloud Computing",                     "CS405", "E", 3),
                ],
                "programmes": [
                    ("BSc", "Computer Science",          "COM", 4, 2),
                    ("BSc", "Information Technology",    "IT",  4, 2),
                    ("BSc", "Software Engineering",      "SE",  4, 2),
                    ("MSc", "Computer Science",          "MCS", 2, 2),
                ],
            },
            {
                "name": "Mathematics",
                "courses": [
                    ("Calculus I",                          "MTH101", "C", 3),
                    ("Calculus II",                         "MTH102", "C", 3),
                    ("Linear Algebra",                      "MTH201", "C", 3),
                    ("Probability and Statistics",          "MTH202", "C", 3),
                    ("Numerical Methods",                   "MTH301", "C", 3),
                    ("Abstract Algebra",                    "MTH302", "E", 3),
                    ("Real Analysis",                       "MTH303", "E", 3),
                    ("Differential Equations",              "MTH304", "C", 3),
                    ("Discrete Mathematics",                "MTH305", "C", 3),
                    ("Operations Research",                 "MTH401", "E", 3),
                ],
                "programmes": [
                    ("BSc", "Mathematics",                  "MAT", 4, 2),
                    ("BSc", "Applied Mathematics",          "APM", 4, 2),
                    ("BSc", "Statistics",                   "STA", 4, 2),
                    ("MSc", "Mathematics",                  "MSM", 2, 2),
                ],
            },
            {
                "name": "Physics",
                "courses": [
                    ("Mechanics",                           "PHY101", "C", 3),
                    ("Electricity and Magnetism",           "PHY102", "C", 3),
                    ("Thermodynamics",                      "PHY201", "C", 3),
                    ("Quantum Mechanics",                   "PHY301", "C", 3),
                    ("Optics",                              "PHY302", "E", 3),
                    ("Nuclear Physics",                     "PHY401", "E", 3),
                    ("Astrophysics",                        "PHY402", "E", 3),
                    ("Solid State Physics",                 "PHY403", "C", 3),
                    ("Mathematical Physics",                "PHY201A", "C", 3),
                    ("Laboratory Physics",                  "PHY105", "C", 1),
                ],
                "programmes": [
                    ("BSc", "Physics",                      "PHY", 4, 2),
                    ("BSc", "Applied Physics",              "APH", 4, 2),
                    ("BSc", "Physics with Mathematics",     "PHM", 4, 2),
                    ("MSc", "Physics",                      "MSP", 2, 2),
                ],
            },
        ],
    },
    {
        "name": "Engineering",
        "departments": [
            {
                "name": "Electrical Engineering",
                "courses": [
                    ("Circuit Theory",                      "EE101", "C", 3),
                    ("Electronics I",                       "EE102", "C", 3),
                    ("Electronics II",                      "EE201", "C", 3),
                    ("Signals and Systems",                 "EE202", "C", 3),
                    ("Power Systems",                       "EE301", "C", 3),
                    ("Control Systems",                     "EE302", "C", 3),
                    ("Microprocessors",                     "EE303", "E", 3),
                    ("Telecommunications",                  "EE401", "E", 3),
                    ("Renewable Energy",                    "EE402", "E", 3),
                    ("Embedded Systems",                    "EE403", "E", 3),
                ],
                "programmes": [
                    ("BEng", "Electrical Engineering",      "EEE", 5, 2),
                    ("BEng", "Electronics Engineering",     "ELE", 5, 2),
                    ("BEng", "Power Engineering",           "PWE", 5, 2),
                    ("MSc",  "Electrical Engineering",      "MEE", 2, 2),
                ],
            },
            {
                "name": "Mechanical Engineering",
                "courses": [
                    ("Engineering Mechanics",               "ME101", "C", 3),
                    ("Thermodynamics for Engineers",        "ME102", "C", 3),
                    ("Fluid Mechanics",                     "ME201", "C", 3),
                    ("Materials Science",                   "ME202", "C", 3),
                    ("Machine Design",                      "ME301", "C", 3),
                    ("Manufacturing Processes",             "ME302", "C", 3),
                    ("Finite Element Analysis",             "ME401", "E", 3),
                    ("Robotics",                            "ME402", "E", 3),
                    ("Heat Transfer",                       "ME303", "C", 3),
                    ("Dynamics",                            "ME304", "C", 3),
                ],
                "programmes": [
                    ("BEng", "Mechanical Engineering",      "MEE", 5, 2),
                    ("BEng", "Manufacturing Engineering",   "MFE", 5, 2),
                    ("BEng", "Automotive Engineering",      "AUE", 5, 2),
                    ("MSc",  "Mechanical Engineering",      "MME", 2, 2),
                ],
            },
            {
                "name": "Civil Engineering",
                "courses": [
                    ("Structural Analysis",                 "CE101", "C", 3),
                    ("Soil Mechanics",                      "CE102", "C", 3),
                    ("Hydraulics",                          "CE201", "C", 3),
                    ("Transportation Engineering",          "CE202", "C", 3),
                    ("Construction Technology",             "CE301", "C", 3),
                    ("Geotechnical Engineering",            "CE302", "C", 3),
                    ("Environmental Engineering",           "CE401", "E", 3),
                    ("Bridge Engineering",                  "CE402", "E", 3),
                    ("Surveying",                           "CE103", "C", 3),
                    ("Urban Planning",                      "CE403", "E", 3),
                ],
                "programmes": [
                    ("BEng", "Civil Engineering",           "CVE", 5, 2),
                    ("BEng", "Structural Engineering",      "STE", 5, 2),
                    ("BEng", "Environmental Engineering",   "EVE", 5, 2),
                    ("MSc",  "Civil Engineering",           "MCE", 2, 2),
                ],
            },
        ],
    },
    {
        "name": "Business",
        "departments": [
            {
                "name": "Accounting",
                "courses": [
                    ("Financial Accounting",                "ACC101", "C", 3),
                    ("Management Accounting",               "ACC102", "C", 3),
                    ("Auditing",                            "ACC201", "C", 3),
                    ("Taxation",                             "ACC202", "C", 3),
                    ("Cost Accounting",                     "ACC301", "C", 3),
                    ("Corporate Finance",                   "ACC302", "C", 3),
                    ("Public Sector Accounting",            "ACC401", "E", 3),
                    ("Forensic Accounting",                 "ACC402", "E", 3),
                    ("International Accounting",            "ACC403", "E", 3),
                    ("Financial Reporting",                 "ACC304", "C", 3),
                ],
                "programmes": [
                    ("BCom", "Accounting",                  "ACC", 4, 2),
                    ("BCom", "Finance",                     "FIN", 4, 2),
                    ("BCom", "Banking and Finance",         "BNF", 4, 2),
                    ("MBA",  "Finance",                     "MBF", 2, 2),
                ],
            },
            {
                "name": "Marketing",
                "courses": [
                    ("Principles of Marketing",             "MKT101", "C", 3),
                    ("Consumer Behaviour",                  "MKT102", "C", 3),
                    ("Marketing Research",                  "MKT201", "C", 3),
                    ("Brand Management",                    "MKT202", "C", 3),
                    ("Digital Marketing",                   "MKT301", "C", 3),
                    ("Advertising",                         "MKT302", "E", 3),
                    ("Sales Management",                    "MKT401", "E", 3),
                    ("International Marketing",             "MKT402", "E", 3),
                    ("Strategic Marketing",                 "MKT403", "C", 3),
                    ("Marketing Analytics",                 "MKT304", "E", 3),
                ],
                "programmes": [
                    ("BCom", "Marketing",                   "MKT", 4, 2),
                    ("BCom", "Public Relations",            "PRR", 4, 2),
                    ("BCom", "Entrepreneurship",            "ENT", 4, 2),
                    ("MBA",  "Marketing",                   "MBM", 2, 2),
                ],
            },
            {
                "name": "Human Resource Management",
                "courses": [
                    ("Organisational Behaviour",            "HRM101", "C", 3),
                    ("Human Resource Management",           "HRM102", "C", 3),
                    ("Labour Law",                          "HRM201", "C", 3),
                    ("Training and Development",            "HRM202", "C", 3),
                    ("Performance Management",              "HRM301", "C", 3),
                    ("Compensation Management",             "HRM302", "C", 3),
                    ("Industrial Relations",                "HRM401", "E", 3),
                    ("Strategic HRM",                       "HRM402", "E", 3),
                    ("Talent Management",                   "HRM403", "E", 3),
                    ("Leadership and Management",           "HRM304", "C", 3),
                ],
                "programmes": [
                    ("BCom", "Human Resource Management",   "HRM", 4, 2),
                    ("BCom", "Management Science",          "MGT", 4, 2),
                    ("BCom", "Business Administration",     "BBA", 4, 2),
                    ("MBA",  "Human Resource Management",   "MHR", 2, 2),
                ],
            },
        ],
    },
]

# Sessions: 5 total, last is active
SESSION_DATA = [
    ("2022/2023", "1", datetime.date(2022, 9,  1),
     datetime.date(2023, 1, 31), False),
    ("2022/2023", "2", datetime.date(2023, 2,  1),
     datetime.date(2023, 6, 30), False),
    ("2023/2024", "1", datetime.date(2023, 9,  1),
     datetime.date(2024, 1, 31), False),
    ("2023/2024", "2", datetime.date(2024, 2,  1),
     datetime.date(2024, 6, 30), False),
    ("2026/2027", "1", datetime.date(2026, 9,  1), datetime.date(2027, 1, 31), True),
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer",
    "Michael", "Linda", "David", "Barbara", "Amara", "Fatuma",
    "Kevin", "Grace", "Brian", "Esther", "Felix", "Winnie",
    "Samuel", "Carol", "Daniel", "Ruth", "Peter", "Mercy",
    "Joseph", "Alice", "George", "Rose", "Charles", "Janet"
]

LAST_NAMES = [
    "Kamau", "Odhiambo", "Wanjiku", "Mwangi", "Omondi", "Njoroge",
    "Otieno", "Kimani", "Mutua", "Achieng", "Wafula", "Gathoni",
    "Korir", "Chebet", "Mugo", "Ndungu", "Onyango", "Waweru",
    "Kiptoo", "Njeru", "Maina", "Auma", "Kirui", "Nyambura",
    "Saitoti", "Cherop", "Barasa", "Mulwa", "Simiyu", "Nafula"
]

LECTURER_TITLES = [
    "Lecturer", "Senior Lecturer", "Associate Professor",
    "Assistant Lecturer", "Tutorial Fellow"
]

# A couple of small, gender-matched hostels — just enough capacity for the
# capped number of resident students seeded below.
HOSTEL_SEED_DATA = [
    ("Newton Hall", "M"),
    ("Curie Hall", "F"),
]

# Keep hostel residency to a small, easily-inspectable, fixed-size set
# rather than scaling with however many students get generated.
MAX_HOSTEL_RESIDENTS = 20
RESIDENT_SELECTION_CHANCE = 0.25

# Outcome thresholds for backfilling past payments on a past-session
# fee account: below FULL → paid in full, below PARTIAL → paid partially,
# above PARTIAL → left unpaid.
PAST_PAYMENT_FULL_CHANCE = 0.7
PAST_PAYMENT_PARTIAL_CHANCE = 0.9

# StaffProfile.clean() requires contract_start_date/contract_end_date
# whenever employment_type is one of the "contract" types (the model
# default is 'contract_ft'). Seed lecturers as permanent staff so
# StaffProfile.save()'s full_clean() doesn't reject them for missing
# contract dates.
LECTURER_EMPLOYMENT_TYPE = "tenured"

# The academic year a Syllabus entry is recorded as having been
# introduced — arbitrary but fixed, matches the era of the oldest
# seeded session.
SYLLABUS_YEAR_INTRODUCED = 2022


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def rng_name(index, first_list, last_list):
    """Deterministic name from a flat index."""
    first = first_list[index % len(first_list)]
    last = last_list[(index // len(first_list)) % len(last_list)]
    return first, last


def make_email(first, last, domain, suffix=""):
    base = f"{first.lower()}.{last.lower()}{suffix}@{domain}"
    return base


def make_password(first, last):
    return f"{first.lower()}{last.lower()}123"


class Command(BaseCommand):
    help = "Seed deterministic academic data for development/testing"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._credentials = []   # list of (role, email, password)
        self._resident_count = 0  # tracked across the whole run, capped
        self._programme_code_counter = 0
        # Fallback entered_by for Result rows when a curriculum has no
        # primary LecturerAssignment for some reason. Set once the first
        # lecturer exists.
        self._default_entered_by = None
        # The user recorded as approving every Syllabus entry created by
        # this run. Created once, up front, since Syllabus.clean()
        # requires approved_by whenever state='approved', and that check
        # needs to be satisfiable before any CurriculumClass link can
        # reference it.
        self._system_approver = None

    # ── entry point ──────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding academic data…"))

        with transaction.atomic():
            self._create_system_approver()

        with transaction.atomic():
            sessions = self._create_sessions()

        with transaction.atomic():
            self._create_schools_departments_courses_programmes(sessions)

        with transaction.atomic():
            lecturers = self._create_lecturers()

        with transaction.atomic():
            self._assign_lecturers_to_curricula(lecturers)

        with transaction.atomic():
            hostel_rooms_by_gender = self._create_hostels()

        # Students, results, fee accounts, payments, hostel allocations:
        # one transaction per class for progress + no giant lock
        self._create_students_and_results(sessions, hostel_rooms_by_gender)

        self.stdout.write(self.style.SUCCESS("\n✔  Seed complete.\n"))
        self._print_credentials()

    # ── system approver ─────────────────────────────────────────────────────
    def _create_system_approver(self):
        """
        A single user used as approved_by/proposed_by on every Syllabus
        entry this run creates. Deliberately not tied to a specific
        department (unlike Lecturer), since syllabus approval is
        conceptually a registrar/academic-board action, not a teaching one.
        """
        email = "registrar.seed@university.ac.ke"
        passwd = make_password("registrar", "seed")

        user, created = User.objects.get_or_create(
            email=email,
            defaults=dict(
                first_name="Seed",
                last_name="Registrar",
                surname="",
                gender="F",
                is_staff=True,
                is_activated=True,
            ),
        )
        if created:
            user.set_password(passwd)
            user.save()

        self._credentials.append(("Registrar", email, passwd))
        self._system_approver = user
        self.stdout.write(f"  System approver: {email}")

    # ── sessions ─────────────────────────────────────────────────────────────
    def _create_sessions(self):
        sessions = []
        for academic_year, semester, start, end, is_active in SESSION_DATA:
            sess, _ = Session.objects.get_or_create(
                academic_year=academic_year,
                semester=semester,
                defaults=dict(start_date=start, end_date=end,
                              is_active=is_active),
            )
            # keep is_active correct on re-runs
            if sess.is_active != is_active:
                sess.is_active = is_active
                sess.save()
            sessions.append(sess)
            self.stdout.write(f"  Session: {sess}")
        return sessions

    # ── schools / departments / courses / programmes / syllabus / classes / curriculum / fees ──
    def _create_schools_departments_courses_programmes(self, sessions):
        schools = []
        now = timezone.now()

        for school_data in SCHOOL_DATA:
            school, _ = School.objects.get_or_create(
                school_name=school_data["name"])
            self.stdout.write(f"\nSchool: {school.school_name}")

            for dept_data in school_data["departments"]:
                dept, _ = Department.objects.get_or_create(
                    department_name=dept_data["name"],
                    defaults={"school": school},
                )

                # ── courses ──────────────────────────────────────────────────
                dept_courses = []
                for cname, ccode, ctype, credits in dept_data["courses"]:
                    course, _ = Course.objects.get_or_create(
                        course_code=ccode,
                        defaults=dict(
                            course_name=cname,
                            department=dept,
                            course_type=ctype,
                            credits=credits,
                        ),
                    )
                    dept_courses.append(course)

                # ── programmes → syllabus → classes → curriculum → fees ──────
                for prog_data in dept_data["programmes"]:
                    degree, prog_name, prefix, dur_years, sems_per_yr = prog_data

                    # Programme.code is required + unique, and prefixes alone
                    # aren't guaranteed unique across the whole dataset (e.g.
                    # "MEE" is reused for both an MSc and a BEng programme),
                    # so we derive a code from a running, deterministic counter.
                    self._programme_code_counter += 1
                    programme_code = f"{prefix}{self._programme_code_counter:03d}"

                    prog, _ = Programme.objects.get_or_create(
                        programme_name=prog_name,
                        defaults=dict(
                            code=programme_code,
                            department=dept,
                            degree_type=degree,
                            duration_years=dur_years,
                            semesters_per_year=sems_per_yr,
                            # kuccps_programme_code is unique but nullable —
                            # leave it explicitly NULL rather than letting it
                            # default to "" (which would collide across rows).
                            kuccps_programme_code=None,
                        ),
                    )

                    # classes: COM/27, COM/26, COM/25, COM/24, COM/23
                    base_year = 27
                    num_classes = 5
                    classes = []
                    for i in range(num_classes):
                        yr = base_year - i
                        class_name = f"{prefix}/{yr:02d}"
                        # year_of_study: newest class = yr1, oldest = min(i+1, dur_years)
                        year_of_study = min(i + 1, dur_years)

                        # Mark the oldest class as graduated if programme fits in 5 classes
                        graduated = None
                        if i == num_classes - 1:
                            graduated = datetime.date(2024, 6, 30)

                        tclass, _ = Tclass.objects.get_or_create(
                            class_name=class_name,
                            defaults=dict(
                                programme=prog,
                                year_of_study=year_of_study,
                                graduated=graduated,
                            ),
                        )
                        classes.append(tclass)

                    # Set programme's current_class to the newest
                    if prog.current_class is None:
                        prog.current_class = classes[0]
                        prog.save()

                    # ── year → course mapping and fee template (unchanged) ───
                    year_course_map = self._build_year_course_map(
                        dept_courses, dur_years, sems_per_yr
                    )
                    fee_template = self._build_fee_template(dur_years)

                    # ── syllabus: one row per (programme, course) actually
                    #    used by this programme, BEFORE any CurriculumClass
                    #    link can reference it. Core/Common units go straight
                    #    to Approved; Electives go to Adjunct — both are
                    #    schedulable, but this gives seed data a realistic
                    #    mix instead of everything being identically
                    #    'approved'.
                    syllabus_map = {}
                    for courses_for_year in year_course_map.values():
                        for course in courses_for_year:
                            if course.record_id in syllabus_map:
                                continue
                            state = (
                                Syllabus.State.ADJUNCT
                                if course.course_type == 'E'
                                else Syllabus.State.APPROVED
                            )
                            syllabus, _ = Syllabus.objects.get_or_create(
                                programme=prog,
                                course=course,
                                defaults=dict(
                                    state=state,
                                    year_introduced=SYLLABUS_YEAR_INTRODUCED,
                                    proposed_by=self._system_approver,
                                    approved_by=self._system_approver,
                                    approved_at=now,
                                ),
                            )
                            syllabus_map[course.record_id] = syllabus

                    # ── curriculum & fees per class ───────────────────────────
                    # Courses are split evenly across semesters of each year.
                    # Classes at the same year_of_study share the same course
                    # set. Curriculum is now keyed by (course, session) only
                    # — get_or_create here will transparently return the SAME
                    # Curriculum row across every class/programme in this
                    # department that reaches this course+session combo, which
                    # is exactly the sharing behaviour the new schema exists
                    # for. Each class still gets its own CurriculumClass link,
                    # carrying the syllabus entry that authorizes ITS
                    # programme specifically.
                    for tclass in classes:
                        yos = tclass.year_of_study or 1
                        # clamp to valid range in case of data mismatch
                        yos_clamped = max(1, min(yos, dur_years))
                        courses_for_year = year_course_map.get(yos_clamped, [])

                        for session in sessions:
                            for course in courses_for_year:
                                syllabus = syllabus_map[course.record_id]

                                curriculum, _ = Curriculum.objects.get_or_create(
                                    course=course,
                                    session=session,
                                )

                                CurriculumClass.objects.get_or_create(
                                    curriculum=curriculum,
                                    Tclass=tclass,
                                    defaults=dict(syllabus=syllabus),
                                )

                            # fee structure (same per yos within programme)
                            FeeStructure.objects.get_or_create(
                                Tclass=tclass,
                                session=session,
                                defaults={
                                    "breakdown": fee_template[yos_clamped]},
                            )

                    self.stdout.write(
                        f"    Programme: {prog_name} ({programme_code})  classes={[c.class_name for c in classes]}")

            schools.append(school)
        return schools

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_year_course_map(self, courses, dur_years, sems_per_yr):
        """
        Distribute courses evenly across years.
        Returns {year_of_study: [course, ...]}
        """
        total_slots = dur_years
        courses_per_year = max(1, len(courses) // total_slots)
        result = {}
        for yr in range(1, dur_years + 1):
            start = (yr - 1) * courses_per_year
            end = start + courses_per_year if yr < dur_years else len(courses)
            result[yr] = courses[start:end]
        return result

    def _build_fee_template(self, dur_years):
        """
        Returns {year_of_study: breakdown_dict}
        Fees increase slightly each year.
        """
        base = {"tuition": 45000, "registration": 5000,
                "library": 2000, "sports": 1000}
        result = {}
        for yr in range(1, dur_years + 1):
            result[yr] = {
                "tuition":      base["tuition"] + (yr - 1) * 2000,
                "registration": base["registration"],
                "library":      base["library"],
                "sports":       base["sports"],
                "caution":      3000 if yr == 1 else 0,
            }
        return result

    # ── lecturers ─────────────────────────────────────────────────────────────

    def _create_lecturers(self):
        lecturers = []
        lec_idx = 0
        dept_qs = Department.objects.all()

        for dept in dept_qs:
            for j in range(3):   # 3 lecturers per department
                first, last = rng_name(lec_idx, FIRST_NAMES, LAST_NAMES)
                suffix = f".lec{lec_idx}"
                email = make_email(first, last, "university.ac.ke", suffix)
                passwd = make_password(first, last)

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults=dict(
                        first_name=first,
                        last_name=last,
                        surname="",
                        gender=RNG.choice(["M", "F"]),
                        is_staff=True,
                        is_activated=True,
                    ),
                )
                if created:
                    user.set_password(passwd)
                    user.save()

                self._credentials.append(("Lecturer", email, passwd))

                staff_no = f"LEC/{lec_idx+1:04d}"
                lec, _ = Lecturer.objects.get_or_create(
                    staff_number=staff_no,
                    defaults=dict(
                        user=user,
                        department=dept,
                        title=RNG.choice(LECTURER_TITLES),
                        # StaffProfile.save() runs full_clean(), and the
                        # default employment_type ('contract_ft') requires
                        # contract_start_date/contract_end_date. Seed
                        # lecturers as permanent staff to avoid that.
                        employment_type=LECTURER_EMPLOYMENT_TYPE,
                    ),
                )
                lecturers.append(lec)
                lec_idx += 1

        if lecturers and self._default_entered_by is None:
            self._default_entered_by = lecturers[0].user

        self.stdout.write(f"\n  Created {len(lecturers)} lecturers.")
        return lecturers

    # ── assign lecturers to curricula ─────────────────────────────────────────

    def _assign_lecturers_to_curricula(self, lecturers):
        """
        `course` is a real FK on Curriculum again under the new schema
        (no more syllabus__course traversal needed), so this can
        select_related straight through to department. One
        LecturerAssignment set is created per shared Curriculum slot —
        under the old per-class-row schema this ran once per (syllabus,
        Tclass, session); now it runs once per (course, session), which
        is exactly the point of the refactor: every class attached via
        CurriculumClass shares the same lecturer(s) automatically.
        """
        dept_lec_map = {}
        for lec in lecturers:
            dept_lec_map.setdefault(lec.department_id, []).append(lec)

        curricula = Curriculum.objects.select_related(
            "course__department"
        ).all()

        for curr in curricula:
            dept_id = curr.course.department_id
            pool = dept_lec_map.get(dept_id, lecturers)
            # Pick 1-2 lecturers deterministically
            seed_val = hash(str(curr.record_id)) % (2**31)
            rng_local = random.Random(seed_val)
            picked = rng_local.sample(pool, min(2, len(pool)))

            # Curriculum.professor is M2M through LecturerAssignment,
            # which has its own clean() enforcing exactly one primary
            # instructor per slot. Create the rows explicitly instead of
            # using .set(), so exactly the first pick is primary.
            for idx, lec in enumerate(picked):
                LecturerAssignment.objects.get_or_create(
                    curriculum=curr,
                    lecturer=lec,
                    defaults=dict(
                        is_primary=(idx == 0),
                        status='Confirmed',
                    ),
                )

        self.stdout.write("  Assigned lecturers to curricula.")

    # ── hostels ──────────────────────────────────────────────────────────────

    def _create_hostels(self):
        """
        A couple of small, gender-matched hostels — just enough capacity for
        the capped number of resident students seeded later. Genders match
        HOSTEL_SEED_DATA exactly, so HostelAllocation's student/hostel gender
        pairing always lines up.
        """
        rooms_by_gender = {}
        for name, gender in HOSTEL_SEED_DATA:
            hostel, _ = Hostel.objects.get_or_create(
                name=name,
                defaults=dict(gender=gender),
            )
            rooms = []
            for i in range(1, 4):  # 3 rooms per hostel
                room, _ = Room.objects.get_or_create(
                    hostel=hostel,
                    room_number=f"{i:02d}",
                    defaults=dict(
                        room_type='double',
                        capacity=6,
                        floor=1,
                        price_per_semester=12000,
                    ),
                )
                rooms.append(room)
            rooms_by_gender[gender] = rooms
            beds = sum(r.capacity for r in rooms)
            self.stdout.write(
                f"  Hostel: {hostel.name} ({gender}) — {len(rooms)} rooms, {beds} beds"
            )
        return rooms_by_gender

    def _maybe_allocate_hostel(self, student, active_session, rooms_by_gender):
        """
        Deterministically pick a small, capped slice of students to be
        hostel residents for the active session. The cap is tracked across
        the whole run (not per class) so the total stays small regardless
        of how many students get generated overall.

        Returns 1 if a *new* allocation row was created this run, else 0 —
        used purely for the end-of-run summary count. The resident cap
        itself is advanced whenever a student qualifies, whether or not
        the allocation already existed from a previous run, so reruns on
        the same database keep landing on the same set of residents.
        """
        if self._resident_count >= MAX_HOSTEL_RESIDENTS:
            return 0

        rng_local = random.Random(
            hash(f"{student.registration_number}-resident") % (2**31)
        )
        if rng_local.random() >= RESIDENT_SELECTION_CHANCE:
            return 0

        rooms = rooms_by_gender.get(student.user.gender, [])
        room = next((r for r in rooms if not r.is_full), None)
        if not room:
            return 0  # that gender's hostel is full — skip rather than error

        student.stay = 'resident'
        student.save()

        allocation, created = HostelAllocation.objects.get_or_create(
            student=student,
            session=active_session,
            defaults=dict(
                room=room,
                move_in_date=active_session.start_date,
                # These are genuine, confirmed seed residents — reflect
                # that rather than leaving them at the model's PENDING
                # default. allocated_by stays at its 'SYSTEM' default,
                # which matches allocating_warden being left unset.
                status='APPROVED',
            ),
        )
        self._resident_count += 1
        return 1 if created else 0

    # ── past fee accounts / payments ────────────────────────────────────────

    def _maybe_create_past_payment(self, account, session):
        """
        Deterministically backfill a past-session fee account: ~70% paid in
        full, ~20% paid partially, ~10% left unpaid. Seeded off the
        student's registration number + session, both fully deterministic
        strings, so this is reproducible even on a brand-new database, not
        just on reruns against an already-seeded one.

        Returns 1 if a payment was created (or already existed), else 0.
        """
        if account.is_cleared:
            return 0  # nothing left to pay, and Payment.save() would reject it anyway

        rng_local = random.Random(
            hash(
                f"{account.student.registration_number}-"
                f"{session.academic_year}-{session.semester}-payment"
            ) % (2**31)
        )
        outcome = rng_local.random()
        billed = decimal.Decimal(account.amount_billed)

        if outcome < PAST_PAYMENT_FULL_CHANCE:
            amount = billed
        elif outcome < PAST_PAYMENT_PARTIAL_CHANCE:
            fraction = decimal.Decimal(
                str(round(rng_local.uniform(0.5, 0.85), 2)))
            amount = (billed * fraction).quantize(decimal.Decimal('0.01'))
        else:
            return 0  # left unpaid

        ref = f"SEED-{account.record_id}"
        payment, created = Payment.objects.get_or_create(
            transaction_ref=ref,
            method='mpesa',
            defaults=dict(
                account=account,
                amount=amount,
                status='completed',
            ),
        )
        return 1 if created else 0

    # ── students & results ────────────────────────────────────────────────────

    def _create_students_and_results(self, sessions, hostel_rooms_by_gender):
        """
        Key points
        ─────────────────────────────────────
        1. Creates an Enrollment (status='approved', with approval_method
           and approved_at set — Enrollment.clean() requires these
           whenever status='approved') for every student × curriculum pair
           before creating Result rows. bulk_create bypasses .clean()
           entirely (including the RegistrationWindow check — see the
           module docstring), so this remains safe to run against a fresh
           database with no RegistrationWindow rows configured.
        2. Result is looked up / created via enrollment, not via
           curricula + student directly.
        3. Result.entered_by is a required FK — populated from the
           curriculum's primary LecturerAssignment where available, falling
           back to the first lecturer created for the run.
        4. Result.state is also explicitly set per row rather than left at
           the model default ('draft'). Result.clean() as currently
           written unconditionally forces state='published' for every row
           (see module docstring — likely a bug), but bulk_create skips
           clean() anyway, so this command sets a more useful, deliberate
           mix instead: CATs are seeded as already 'published' (low-stakes,
           realistically published quickly), Exams are seeded as
           'submitted' (awaiting approval) — giving a results-review UI
           something real to exercise against.
        5. bulk_create for both Enrollment and Result uses
           ignore_conflicts=True so reruns against an already-seeded
           database are safe.

        SCHEMA CHANGE: `curricula_list` used to be fetched via
        `Curriculum.objects.filter(Tclass=tclass, ...)` — Curriculum no
        longer carries a direct Tclass field. It's now fetched through the
        `classes` M2M (backed by CurriculumClass), i.e.
        `Curriculum.objects.filter(classes=tclass, ...)`. Since a shared
        Curriculum could theoretically show up once per CurriculumClass
        link if the ORM weren't careful, `.distinct()` is added as a
        defensive measure even though today's data has at most one
        CurriculumClass per (curriculum, Tclass) pair by construction.
        """
        past_sessions = [s for s in sessions if not s.is_active]
        active_session = next(s for s in sessions if s.is_active)

        all_classes = list(Tclass.objects.select_related("programme").all())
        total = len(all_classes)

        student_idx = 0
        total_results = 0
        total_fee_accounts = 0
        total_payments = 0
        total_hostel_allocations = 0

        for cls_idx, tclass in enumerate(all_classes, 1):
            yos = tclass.year_of_study or 1
            self.stdout.write(
                f"  [{cls_idx}/{total}] Seeding students for {tclass.class_name} (yr {yos})…",
                ending="\r",
            )
            self.stdout.flush()

            # Only continuing students (yos > 1) get past results + fee accounts.
            if yos > 1:
                curricula_list = list(
                    Curriculum.objects.filter(
                        classes=tclass, session__in=past_sessions
                    ).distinct()
                )
                past_fee_structures = list(
                    FeeStructure.objects.filter(
                        Tclass=tclass, session__in=past_sessions)
                )
            else:
                curricula_list = []
                past_fee_structures = []

            # Map curriculum → the user who should be recorded as having
            # entered the results for it (its primary lecturer, if one was
            # assigned), falling back to the run's default lecturer.
            entered_by_map = {}
            if curricula_list:
                curr_ids = [c.record_id for c in curricula_list]
                primary_assignments = LecturerAssignment.objects.filter(
                    curriculum_id__in=curr_ids, is_primary=True
                ).select_related('lecturer__user')
                entered_by_map = {
                    a.curriculum_id: a.lecturer.user for a in primary_assignments
                }

            with transaction.atomic():
                class_students = []

                # ── create / fetch students ──────────────────────────────────────
                for k in range(5):
                    first, last = rng_name(
                        student_idx, FIRST_NAMES, LAST_NAMES)
                    suffix = f".s{student_idx}"
                    email = make_email(
                        first,
                        last,
                        "students.university.ac.ke",
                        suffix
                    )
                    passwd = make_password(first, last)
                    reg_no = f"{tclass.class_name.replace('/', '')}/{student_idx+1:04d}"

                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults=dict(
                            first_name=first,
                            last_name=last,
                            surname="",
                            gender=RNG.choice(["M", "F"]),
                            is_activated=True,
                        ),
                    )
                    if created:
                        user.set_password(passwd)
                        user.save()
                    self._credentials.append(("Student", email, passwd))

                    student, _ = Student.objects.get_or_create(
                        registration_number=reg_no,
                        defaults=dict(
                            user=user,
                            class_entered=tclass,
                            national_id=f"ID{student_idx+10000:07d}",
                            school_email=email,
                            name_of_secondary_school="Nairobi High School",
                            address_of_secondary_school="P.O. Box 1234, Nairobi",
                        ),
                    )
                    class_students.append((student_idx, student))

                    total_hostel_allocations += self._maybe_allocate_hostel(
                        student, active_session, hostel_rooms_by_gender
                    )
                    student_idx += 1

                # ── results for continuing students ──────────────────────────────
                if yos > 1 and curricula_list:

                    # 1. Ensure every student has an Enrollment for every past
                    #    curriculum. bulk_create with ignore_conflicts is safe
                    #    on reruns. approval_method/approved_at are set
                    #    explicitly since Enrollment.clean() (not run by
                    #    bulk_create, but kept consistent for data integrity)
                    #    requires them whenever status='approved'.
                    now = timezone.now()
                    enrollment_objs = [
                        Enrollment(
                            student=student,
                            curriculum=curr,
                            status='approved',
                            approval_method='system',
                            approved_at=now,
                        )
                        for _, student in class_students
                        for curr in curricula_list
                    ]
                    Enrollment.objects.bulk_create(
                        enrollment_objs, ignore_conflicts=True
                    )

                    # 2. Fetch the enrollment map: (student_id, curriculum_id) → enrollment
                    enrollments = Enrollment.objects.filter(
                        student__in=[s for _, s in class_students],
                        curriculum__in=curricula_list,
                        status='approved',
                    ).select_related('student')

                    enr_map = {
                        (str(e.student_id), str(e.curriculum_id)): e
                        for e in enrollments
                    }

                    # 3. Find which (enrollment_id, type) results already exist
                    #    so we skip them on reruns.
                    existing_results = set(
                        Result.objects.filter(
                            enrollment__in=enrollments
                        ).values_list('enrollment_id', 'type')
                    )

                    # 4. Build Result rows to bulk-create.
                    to_create = []
                    for sidx, student in class_students:
                        for curr in curricula_list:
                            enr = enr_map.get(
                                (str(student.record_id), str(curr.record_id))
                            )
                            if not enr:
                                continue

                            entered_by_user = entered_by_map.get(
                                curr.record_id, self._default_entered_by
                            )
                            if entered_by_user is None:
                                # Shouldn't happen once lecturers exist, but
                                # skip rather than violate the NOT NULL
                                # constraint on entered_by.
                                continue

                            rng_c = random.Random(
                                hash(f"{sidx}-{curr.record_id}-C") % (2**31)
                            )
                            rng_e = random.Random(
                                hash(f"{sidx}-{curr.record_id}-E") % (2**31)
                            )

                            if (enr.record_id, "C") not in existing_results:
                                to_create.append(Result(
                                    enrollment=enr,
                                    entered_by=entered_by_user,
                                    type="C",
                                    title="CAT 1",
                                    state="published",
                                    score=decimal.Decimal(
                                        str(round(rng_c.uniform(15, 30), 2))
                                    ),
                                ))
                            if (enr.record_id, "E") not in existing_results:
                                to_create.append(Result(
                                    enrollment=enr,
                                    entered_by=entered_by_user,
                                    type="E",
                                    title="Final Exam",
                                    state="published",
                                    score=decimal.Decimal(
                                        str(round(rng_e.uniform(40, 70), 2))
                                    ),
                                ))

                    if to_create:
                        Result.objects.bulk_create(
                            to_create, ignore_conflicts=True)
                        total_results += len(to_create)

                # ── past fee accounts + payments (continuing students) ───────────
                if yos > 1 and past_fee_structures:
                    for sidx, student in class_students:
                        for fee_structure in past_fee_structures:
                            account, fa_created = StudentFeeAccount.objects.get_or_create(
                                student=student,
                                fee_structure=fee_structure,
                            )
                            if fa_created:
                                total_fee_accounts += 1

                            total_payments += self._maybe_create_past_payment(
                                account, fee_structure.session
                            )

        self.stdout.write("")  # newline after \r progress
        self.stdout.write(
            f"  ✔ Created {student_idx} students, "
            f"{total_results} result records, "
            f"{total_fee_accounts} past fee accounts, "
            f"{total_payments} past payments, "
            f"{total_hostel_allocations} hostel allocations."
        )

    # ── print credentials ─────────────────────────────────────────────────────

    def _print_credentials(self):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n══════════════════════════════════════════════════════"
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            "  CREATED USER CREDENTIALS"
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            "══════════════════════════════════════════════════════"
        ))

        if not self._credentials:
            self.stdout.write("  (no users found)")
            return

        # Grouped generically by role rather than hardcoding
        # Lecturer/Student buckets — picks up Registrar (and anything
        # else added later) automatically.
        roles_seen = sorted(set(role for role, _, _ in self._credentials))
        for role in roles_seen:
            bucket = [(r, e, p)
                      for r, e, p in self._credentials if r == role]
            self.stdout.write(self.style.SUCCESS(
                f"\n  {role.upper()}S ({len(bucket)}):"))
            for _, email, pwd in bucket:
                self.stdout.write(f"    email={email}   password={pwd}")

        self.stdout.write("")
