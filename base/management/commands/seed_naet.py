from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import Institution, School, Department, Office

import random
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


def make_logo(initials="NU", size=256):
    """Generate a simple random-coloured logo and return PNG bytes."""
    bg = tuple(random.randint(30, 180) for _ in range(3))
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)

    # white ring
    pad = size // 10
    draw.ellipse([pad, pad, size - pad, size - pad], outline="white", width=8)

    # initials in the centre
    try:
        font = ImageFont.load_default(size=size // 3)   # Pillow 10.1+
    except TypeError:
        font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), initials, font=font)
    draw.text(
        ((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top),
        initials, fill="white", font=font,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


CONTACT_FIELDS = (
    "email", "phone_number", "alternate_phone_number",
    "address", "city", "state", "website",
)

INSTITUTION = {
    "institution_name": "Naet University",
    "charter_number": "Naet University Charter, 2026",
    "email": "naet@naetuniversity.com",
    "phone_number": "0721546789",
    "alternate_phone_number": "0765784939",
    "address": "Matunda, Seku, Kenya",
    "website": "https://thelaughingbett.github.io/Naet/",
}

SCHOOLS = [
    {
        "school_name": "Science",
        "email": "schoolofscience@naetuniversity.com",
        "phone_number": "0756342387",
        "alternate_phone_number": "0789655467",
        "departments": [
            {
                "department_name": "Mathematics and Computer Science",
                "email": "mathandcs@naetuniversity.com",
                "phone_number": "0789657876",
                "alternate_phone_number": "0754762389",
            },
        ],
    },
]

OFFICES = [
    ("Admission Office", "admissions", "admissions@naetuniversity.com",
     "0767542309", "0789675643", "https://admissions.naetuniversity.com"),
    ("Student Support", "student_support", "support@naetuniversity.com",
     "0745678769", "0789675368", "https://support.naetuniversity.com"),
    ("Registrar", "registrar", "registrar@naetuniversity.com", "0711000001", "", ""),
    ("Bursar", "bursar", "bursar@naetuniversity.com", "0711000002", "", ""),
    ("Finance Office", "finance", "finance@naetuniversity.com", "0711000003", "", ""),
    ("IT Helpdesk", "it_helpdesk", "helpdesk@naetuniversity.com", "0711000004", "", ""),
    ("Library", "library", "library@naetuniversity.com", "0711000005", "", ""),
    ("Human Resources", "hr", "hr@naetuniversity.com", "0711000006", "", ""),
    ("Exam Office", "exam", "exams@naetuniversity.com", "0711000007", "", ""),
]


def save_clean(obj, data):
    """Apply contact fields, run validators, then save."""
    for f in CONTACT_FIELDS:
        if f in data:
            setattr(obj, f, data[f] or None)
    obj.full_clean()
    obj.save()
    return obj


class Command(BaseCommand):
    help = "Seed Naet University with a school, department and offices (safe to re-run)."

    @transaction.atomic
    def handle(self, *args, **opts):
        inst, _ = Institution.objects.get_or_create(
            institution_name=INSTITUTION["institution_name"],
            defaults={"charter_number": INSTITUTION["charter_number"]},
        )

        if not inst.logo:   # only generate once, so re-runs don't pile up files
            inst.logo.save(
                "naet_logo.png",
                ContentFile(make_logo()),
                save=False
            )

        save_clean(inst, INSTITUTION)

        for s in SCHOOLS:
            school, _ = School.objects.get_or_create(
                school_name=s["school_name"])
            # schools/departments share the institution's address and website
            save_clean(
                school, {**s, "address": inst.address, "website": inst.website})

            for d in s["departments"]:
                dept, _ = Department.objects.get_or_create(
                    department_name=d["department_name"], school=school
                )
                save_clean(
                    dept, {**d, "address": inst.address, "website": inst.website})

        for name, otype, email, phone, alt, site in OFFICES:
            office, _ = Office.objects.get_or_create(
                office_name=name, institution=inst,
                defaults={"office_type": otype},
            )
            office.office_type = otype
            save_clean(office, {
                "email": email, "phone_number": phone,
                "alternate_phone_number": alt, "website": site,
                "address": inst.address,
            })

        self.stdout.write(self.style.SUCCESS("Seeded Naet University."))
