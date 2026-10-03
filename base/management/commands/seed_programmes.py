from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import Department, Programme, School, Tclass

INTAKE_YEAR = 2026
INTAKE_SHORT = str(INTAKE_YEAR)[-2:]   # "26"

# (kuccps_code, code, name, degree_type, years, school, department)
PROGRAMMES = [
    ("1101001", "CS", "Computer Science", "BSc",
     4, "Science", "Mathematics and Computer Science"),
    ("1102002", "MBCHB",    "Bachelor of Medicine and Surgery",
     "MBChB", 6, "Medicine and Health Sciences",   "Clinical Medicine"),
    ("1103003", "BED-ARTS", "Bachelor of Education (Arts)",
     "BEd",   4, "Education",                      "Education Arts"),
    ("1104004", "BSC-CE",   "BSc Civil Engineering",            "BEng",
     5, "Engineering",                    "Civil Engineering"),
    ("1105005", "BCOM",     "Bachelor of Commerce",             "BCom",
     4, "Business",                       "Business Administration"),
    ("1106006", "BSC-AGR",  "BSc Agriculture",                  "BSc",
     4, "Agriculture",                    "Agricultural Sciences"),
    ("1107007", "BPHARM",   "Bachelor of Pharmacy",
     "BPharm", 5, "Medicine and Health Sciences",  "Pharmacy"),
    ("1108008", "LLB",      "Bachelor of Laws (LLB)",
     "LLB",   4, "Law",                            "Private Law"),
]


class Command(BaseCommand):
    help = "Seed schools, departments, programmes and year-1 classes (safe to re-run)."

    @transaction.atomic
    def handle(self, *args, **opts):
        for kcode, code, name, degree, years, school_name, dept_name in PROGRAMMES:
            school, _ = School.objects.get_or_create(school_name=school_name)
            dept, _ = Department.objects.get_or_create(
                department_name=dept_name, school=school
            )

            programme, _ = Programme.objects.update_or_create(
                kuccps_programme_code=kcode,
                defaults={
                    "code": code,
                    "programme_name": name,
                    "degree_type": degree,
                    "level": "Undergraduate",
                    "status": "Active",
                    "duration_years": years,
                    "department": dept,
                },
            )

            tclass, _ = Tclass.objects.get_or_create(
                programme=programme,
                year_of_study=1,
                class_name=f"{code}/{INTAKE_SHORT}",   # e.g. BSC-CS/26
            )

            if programme.current_class_id != tclass.pk:
                programme.current_class = tclass
                programme.save(update_fields=["current_class"])

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(PROGRAMMES)} programmes with year-1 classes."
        ))
