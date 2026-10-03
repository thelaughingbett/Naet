import datetime
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import Student, Tclass, User
from base.models.student.reference import KENYAN_COUNTIES

COUNTY_CODES = {name: code for code, name in KENYAN_COUNTIES}
DEV_PASSWORD = "ChangeMe123!"   # dev/test only


def split_name(full_name):
    parts = full_name.split()
    first, last = parts[0], parts[-1]
    middle = " ".join(parts[1:-1]) or None
    return first, middle, last


class Command(BaseCommand):
    help = "Create users and students from a mock KUCCPS placement JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="students.json")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(
                f"{path} not found. Use --file path/to/students.json")

        rows = json.loads(path.read_text(encoding="utf-8"))
        created = skipped = 0
        seeded = []

        for n, row in enumerate(rows, start=1):
            # KCSE index digits double as a fake, deterministic national ID,
            # which is also what makes re-runs idempotent
            national_id = row["kcse_index_no"].split("/")[0][:8]
            if Student.objects.filter(national_id=national_id).exists():
                skipped += 1
                continue

            tclass = Tclass.objects.filter(
                programme__kuccps_programme_code=row["programme_code"],
                year_of_study=1,
            ).first()

            if not tclass:
                raise CommandError(
                    f"No class for programme {row['programme_code']}. "
                    "Run seed_programmes first."
                )

            county_code = COUNTY_CODES.get(row["county"])
            if not county_code:
                raise CommandError(f"Unknown county '{row['county']}'")

            first, middle, last = split_name(row["full_name"])
            school_email = f"{first}.{last}@students.naetuniversity.com".lower()

            with transaction.atomic():
                user = User.objects.create_user(
                    email=row["email"],
                    password=DEV_PASSWORD,
                    first_name=first,
                    surname=middle,
                    last_name=last,
                    gender=row["gender"],
                )

                student = Student(
                    user=user,
                    admission_pathway="KUCCPS",
                    registration_number=f"{row['programme_code']}/{n:04d}/{str(row['placement_year'])[-2:]}",
                    national_id=national_id,
                    school_email=school_email,
                    telephone_no=row["phone"],
                    county=county_code,
                    place_of_birth=row["county"],
                    home_address=row["county"],
                    date_of_birth=datetime.date(
                        2006, 1, 1) + datetime.timedelta(days=n * 37),
                    kcse_mean_grade=row["kcse_mean_grade"],
                    class_entered=tclass,
                    current_class=tclass,
                    disabled=bool(row["special_needs"]),
                    disability_status="Physical" if row["special_needs"] else "None",
                    name_of_secondary_school=f"{row['county']} High School",
                    address_of_secondary_school=row["county"],
                )

                student.full_clean()
                student.save()
                created += 1
                seeded.append(
                    (
                        # collapses the double space when surname is empty
                        " ".join(user.full_name.split()),
                        student.admission_pathway,
                        student.school_email,
                        student.registration_number,
                    )
                )

        self.stdout.write(self.style.SUCCESS(
            f"Students created: {created}, skipped (already exist): {skipped}"
        ))

        if seeded:
            self.stdout.write("")
            self.stdout.write(
                f"{'NAME':<28}{'ADMISSION':<10}{'SCHOOL EMAIL':<46}REG NO"
            )
            self.stdout.write("-" * 110)
            for name, pathway, email, reg in seeded:
                self.stdout.write(f"{name:<28}{pathway:<10}{email:<46}{reg}")
