"""
Management command: seed_academic_data
Usage: python manage.py seed_academic_data

Generates deterministic (replicable) seed data:
  - 3 Schools  →  Departments  →  Courses  →  Programmes  →  Classes
  - Sessions (5, last one active: 2026/2027 Sem 1)
  - Curriculum records per class per session (same year-of-study = same courses)
  - Lecturers assigned to curricula
  - FeeStructures (same year-of-study = same fees within a programme)
  - Students (skipping first-year students for results)
  - Results for non-first-year students
  - Prints all created user credentials
"""

import datetime
import decimal
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

# ── adjust these import paths to match your project layout ──────────────────
from base.models import (
    Course,
    Department,
    Programme,
    School,
    Session,
    Tclass,
    Curriculum,
    Result,
    FeeStructure,
    Lecturer,
    Student
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
                    ("Taxation",                            "ACC202", "C", 3),
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

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer",
               "Michael", "Linda", "David", "Barbara", "Amara", "Fatuma",
               "Kevin", "Grace", "Brian", "Esther", "Felix", "Winnie",
               "Samuel", "Carol", "Daniel", "Ruth", "Peter", "Mercy",
               "Joseph", "Alice", "George", "Rose", "Charles", "Janet"]

LAST_NAMES = ["Kamau", "Odhiambo", "Wanjiku", "Mwangi", "Omondi", "Njoroge",
              "Otieno", "Kimani", "Mutua", "Achieng", "Wafula", "Gathoni",
              "Korir", "Chebet", "Mugo", "Ndungu", "Onyango", "Waweru",
              "Kiptoo", "Njeru", "Maina", "Auma", "Kirui", "Nyambura",
              "Saitoti", "Cherop", "Barasa", "Mulwa", "Simiyu", "Nafula"]

LECTURER_TITLES = ["Lecturer", "Senior Lecturer", "Associate Professor",
                   "Assistant Lecturer", "Tutorial Fellow"]


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

    # ── entry point ──────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding academic data…"))

        with transaction.atomic():
            sessions = self._create_sessions()

        with transaction.atomic():
            self._create_schools_departments_courses_programmes(sessions)

        with transaction.atomic():
            lecturers = self._create_lecturers()

        with transaction.atomic():
            self._assign_lecturers_to_curricula(lecturers, sessions)

        # Students and results: one transaction per class for progress + no giant lock
        self._create_students_and_results(sessions)

        self.stdout.write(self.style.SUCCESS("\n✔  Seed complete.\n"))
        self._print_credentials()

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

    # ── schools / departments / courses / programmes / classes / curriculum / fees ──
    def _create_schools_departments_courses_programmes(self, sessions):
        active_session = next(s for s in sessions if s.is_active)
        lecturer_idx = 0
        schools = []

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

                # ── programmes → classes → curriculum → fees ─────────────────
                for prog_data in dept_data["programmes"]:
                    degree, prog_name, prefix, dur_years, sems_per_yr = prog_data
                    prog, _ = Programme.objects.get_or_create(
                        programme_name=prog_name,
                        defaults=dict(
                            department=dept,
                            degree_type=degree,
                            duration_years=dur_years,
                            semesters_per_year=sems_per_yr,
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

                    # ── curriculum & fees per class ───────────────────────────
                    # Courses are split evenly across semesters of each year.
                    # Classes at the same year_of_study share the same course set.
                    # We build a mapping: year_of_study → list of courses
                    year_course_map = self._build_year_course_map(
                        dept_courses, dur_years, sems_per_yr
                    )

                    # fee template per year_of_study
                    fee_template = self._build_fee_template(dur_years)

                    for tclass in classes:
                        yos = tclass.year_of_study or 1
                        # clamp to valid range in case of data mismatch
                        yos_clamped = max(1, min(yos, dur_years))
                        courses_for_year = year_course_map.get(yos_clamped, [])

                        for session in sessions:
                            for course in courses_for_year:
                                Curriculum.objects.get_or_create(
                                    course=course,
                                    Tclass=tclass,
                                    session=session,
                                )

                            # fee structure (same per yos within programme)
                            FeeStructure.objects.get_or_create(
                                Tclass=tclass,
                                session=session,
                                defaults={
                                    "breakdown": fee_template[yos_clamped]},
                            )

                    self.stdout.write(
                        f"    Programme: {prog_name}  classes={[c.class_name for c in classes]}")

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
                        role="staff",
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
                    ),
                )
                lecturers.append(lec)
                lec_idx += 1

        self.stdout.write(f"\n  Created {len(lecturers)} lecturers.")
        return lecturers

    # ── assign lecturers to curricula ─────────────────────────────────────────

    def _assign_lecturers_to_curricula(self, lecturers, sessions):
        # Build dept → lecturers map
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
            curr.professor.set(picked)

        self.stdout.write("  Assigned lecturers to curricula.")

    # ── students & results ────────────────────────────────────────────────────

    def _create_students_and_results(self, sessions):
        past_sessions = [s for s in sessions if not s.is_active]

        all_classes = list(Tclass.objects.select_related("programme").all())
        total = len(all_classes)
        student_idx = 0
        total_results = 0

        for cls_idx, tclass in enumerate(all_classes, 1):
            yos = tclass.year_of_study or 1
            self.stdout.write(
                f"  [{cls_idx}/{total}] Seeding students for {tclass.class_name} (yr {yos})…",
                ending="\r",
            )
            self.stdout.flush()

            # Pre-fetch curricula for this class in past sessions (only needed for yos > 1)
            if yos > 1:
                curricula_list = list(
                    Curriculum.objects.filter(
                        Tclass=tclass, session__in=past_sessions)
                )
            else:
                curricula_list = []

            with transaction.atomic():
                class_students = []

                for k in range(5):
                    first, last = rng_name(
                        student_idx, FIRST_NAMES, LAST_NAMES)
                    suffix = f".s{student_idx}"
                    email = make_email(
                        first, last, "students.university.ac.ke", suffix)
                    passwd = make_password(first, last)
                    reg_no = f"{tclass.class_name.replace('/', '')}/{student_idx+1:04d}"

                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults=dict(
                            first_name=first,
                            last_name=last,
                            surname="",
                            gender=RNG.choice(["M", "F"]),
                            role="student",
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
                    student_idx += 1

                # Bulk-create results for this class
                if yos > 1 and curricula_list:
                    existing = set(
                        Result.objects.filter(
                            curricula__in=curricula_list,
                            student__in=[s for _, s in class_students],
                        ).values_list("curricula_id", "student_id", "type")
                    )

                    to_create = []
                    for sidx, student in class_students:
                        for curr in curricula_list:
                            rng_c = random.Random(
                                hash(f"{sidx}-{str(curr.record_id)}-C") % (2**31)
                            )
                            rng_e = random.Random(
                                hash(f"{sidx}-{str(curr.record_id)}-E") % (2**31)
                            )
                            if (curr.record_id, student.record_id, "C") not in existing:
                                to_create.append(Result(
                                    curricula=curr,
                                    student=student,
                                    type="C",
                                    title="CAT 1",
                                    score=decimal.Decimal(
                                        str(round(rng_c.uniform(15, 30), 2))),
                                ))
                            if (curr.record_id, student.record_id, "E") not in existing:
                                to_create.append(Result(
                                    curricula=curr,
                                    student=student,
                                    type="E",
                                    title="Final Exam",
                                    score=decimal.Decimal(
                                        str(round(rng_e.uniform(40, 70), 2))),
                                ))

                    if to_create:
                        Result.objects.bulk_create(
                            to_create, ignore_conflicts=True)
                        total_results += len(to_create)

        self.stdout.write("")   # newline after \r progress
        self.stdout.write(
            f"  ✔ Created {student_idx} students and {total_results} result records.")

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
            self.stdout.write("  (no new users created — all already exist)")
            return

        lecturers = [(r, e, p)
                     for r, e, p in self._credentials if r == "Lecturer"]
        students = [(r, e, p)
                    for r, e, p in self._credentials if r == "Student"]

        self.stdout.write(self.style.SUCCESS(
            f"\n  LECTURERS ({len(lecturers)}):"))
        for _, email, pwd in lecturers:
            self.stdout.write(f"    email={email}   password={pwd}")

        self.stdout.write(self.style.SUCCESS(
            f"\n  STUDENTS ({len(students)}):"))
        for _, email, pwd in students:
            self.stdout.write(f"    email={email}   password={pwd}")

        self.stdout.write("")
