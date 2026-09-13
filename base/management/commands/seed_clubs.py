# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_clubs
Usage: python manage.py seed_clubs

Seeds Club + ClubPatron rows deterministically.

NOTE: ClubMembership and ClubLeadershipPosition are NOT seeded here —
their field shapes weren't confirmed at the time this was written (only
inferred from Club.current_leadership's `member__student__user` traversal
and Club.active_member_count's `status="active"` filter). Seeding them
blindly risked raising TypeError on every field-name guess. Once those
two models are confirmed, extend _seed_memberships_and_leadership()
below rather than guessing here.
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import (
    Club, ClubPatron, ClubMembership, ClubLeadershipPosition,
    User, Department, Venue, Student,
)

RNG = random.Random(42)

CLUB_DATA = [
    dict(
        name="AI & Machine Learning Society",
        code="AI-ML",
        category="academic",
        description=(
            "Explores artificial intelligence, deep learning, and real-world "
            "ML applications through workshops, hackathons, and guest talks."
        ),
        membership_capacity=150,
        annual_dues=0,
        department_name="Computer Science",
    ),
    dict(
        name="Debate & Oratory Society",
        code="DEBATE",
        category="political",
        description=(
            "Sharpens public speaking and critical thinking through weekly "
            "debates, Model UN training, and inter-college competitions."
        ),
        membership_capacity=100,
        annual_dues=500,
        department_name=None,
    ),
    dict(
        name="Cricket Club",
        code="CRICKET",
        category="sports",
        description=(
            "Regular practice sessions, inter-college tournaments, and "
            "fitness training for cricket enthusiasts of all skill levels."
        ),
        membership_capacity=45,
        annual_dues=1000,
        department_name=None,
    ),
    dict(
        name="Music & Performing Arts Society",
        code="MUSIC-PA",
        category="performing_arts",
        description=(
            "A platform for singers, instrumentalists, and dancers to "
            "perform and collaborate on creative projects across campus."
        ),
        membership_capacity=120,
        annual_dues=0,
        department_name=None,
    ),
    dict(
        name="Entrepreneurship Cell",
        code="E-CELL",
        category="entrepreneurship",
        description=(
            "Fosters innovation and business acumen through guest lectures, "
            "pitch competitions, and startup mentorship programmes."
        ),
        membership_capacity=80,
        annual_dues=0,
        department_name="Marketing",
    ),
    dict(
        name="Robotics & Automation Club",
        code="ROBOTICS",
        category="academic",
        description=(
            "Builds robots and competes in automation challenges using "
            "Arduino, ROS, and other embedded platforms."
        ),
        membership_capacity=65,
        annual_dues=1500,
        department_name="Electrical Engineering",
    ),
    dict(
        name="Christian Union",
        code="CU",
        category="religious",
        description=(
            "Weekly fellowship, bible study groups, and outreach "
            "activities for Christian students across campus."
        ),
        membership_capacity=None,
        annual_dues=0,
        department_name=None,
    ),
    dict(
        name="Environmental Conservation Society",
        code="ECO-SOC",
        category="environment",
        description=(
            "Runs campus clean-up drives, tree-planting initiatives, and "
            "awareness campaigns on sustainability."
        ),
        membership_capacity=None,
        annual_dues=0,
        department_name=None,
    ),
    dict(
        name="Journalism & Media Club",
        code="MEDIA",
        category="media",
        description=(
            "Produces the campus newsletter and covers university events "
            "through writing, photography, and video."
        ),
        membership_capacity=50,
        annual_dues=0,
        department_name=None,
    ),
    dict(
        name="Community Outreach Society",
        code="OUTREACH",
        category="community",
        description=(
            "Organises volunteering drives, donation campaigns, and "
            "partnerships with local community organisations."
        ),
        membership_capacity=None,
        annual_dues=0,
        department_name=None,
    ),
]

# How many active members (beyond the leadership team) to seed per club,
# capped by whatever Student rows already exist in the DB and by the
# club's own membership_capacity if set.
MEMBERS_PER_CLUB = 15

# Leadership positions seeded for every club, in this order. Deliberately
# excludes 'committee_member' — that one allows multiple concurrent
# holders per club (see the model's UniqueConstraint), so it isn't part
# of the fixed "one holder per club" set seeded here.
LEADERSHIP_POSITIONS_TO_SEED = [
    "chairperson",
    "vice_chair",
    "secretary",
    "treasurer",
]

PATRON_TITLES = [
    "Dr.", "Prof.", "Mr.", "Mrs.", "Ms.",
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer",
    "Michael", "Linda", "Amara", "Fatuma", "Felix", "Winnie",
]

LAST_NAMES = [
    "Kamau", "Odhiambo", "Wanjiku", "Mwangi", "Omondi", "Njoroge",
    "Otieno", "Kimani", "Mutua", "Achieng", "Wafula", "Gathoni",
]


class Command(BaseCommand):
    help = "Seed deterministic Club and ClubPatron data for the student club directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing Club rows (cascades ClubPatron) before seeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding clubs…"))

        if options["reset"]:
            deleted_count, _ = Club.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  --reset: deleted {deleted_count} existing club(s) (and their patrons).")
            )

        venues = list(Venue.objects.all())
        created_count = 0

        with transaction.atomic():
            for idx, row in enumerate(CLUB_DATA):
                department = None
                if row["department_name"]:
                    department = Department.objects.filter(
                        department_name=row["department_name"]
                    ).first()
                    if department is None:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ! Department '{row['department_name']}' not found for "
                                f"{row['name']} — leaving department unset. Run "
                                f"seed_academic_data first if you want this populated."
                            )
                        )

                default_venue = None
                if venues:
                    rng_local = random.Random(hash(f"{row['code']}-venue") % (2**31))
                    default_venue = rng_local.choice(venues)

                club, created = Club.objects.get_or_create(
                    code=row["code"],
                    defaults=dict(
                        name=row["name"],
                        category=row["category"],
                        status="active",
                        description=row["description"],
                        department=department,
                        default_meeting_venue=default_venue,
                        membership_capacity=row["membership_capacity"],
                        annual_dues=row["annual_dues"],
                    ),
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  + {club.name}")
                else:
                    self.stdout.write(f"  = {club.name} (already exists, left unchanged)")

                self._seed_patron(club, idx)

        self.stdout.write(
            self.style.SUCCESS(f"\n✔  Seed complete. Created {created_count} club(s).")
        )
        self._seed_memberships_and_leadership()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _seed_patron(self, club, idx):
        """
        Ensures every club has exactly one active primary patron, drawn
        from existing staff Users where possible (falls back to creating
        a dedicated patron user if none exist yet).
        """
        if ClubPatron.objects.filter(club=club, is_active=True, is_primary=True).exists():
            return

        staff_user = User.objects.filter(is_staff=True).order_by('?').first()

        if staff_user is None:
            rng_local = random.Random(hash(f"{club.code}-patron") % (2**31))
            first = rng_local.choice(FIRST_NAMES)
            last = rng_local.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}.patron{idx}@university.ac.ke"
            staff_user, _ = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    first_name=first,
                    last_name=last,
                    surname="",
                    gender=rng_local.choice(["M", "F"]),
                    is_staff=True,
                    is_activated=True,
                ),
            )
            staff_user.set_password(f"{first.lower()}{last.lower()}123")
            staff_user.save()

        ClubPatron.objects.get_or_create(
            club=club,
            staff=staff_user,
            defaults=dict(
                role="patron",
                is_primary=True,
                is_active=True,
            ),
        )

    def _seed_memberships_and_leadership(self):
        """
        For every club: seeds MEMBERS_PER_CLUB active ClubMemberships
        (capped by the club's membership_capacity, if set, and by however
        many Student rows actually exist), then assigns the first four
        as chairperson/vice_chair/secretary/treasurer via
        ClubLeadershipPosition — matching the model's "one active holder
        per (club, position)" constraint.

        Deterministic: each club's member pool is picked via a
        club-seeded RNG shuffle of all Student record_ids, so reruns
        against the same DB always pick the same students.
        """
        all_student_ids = list(Student.objects.values_list('record_id', flat=True))

        if not all_student_ids:
            self.stdout.write(
                self.style.WARNING(
                    "\n  ⚠ No Student rows found — skipped membership/leadership "
                    "seeding. Run seed_academic_data first."
                )
            )
            return

        total_memberships = 0
        total_leadership = 0

        with transaction.atomic():
            for club in Club.objects.all():
                rng_local = random.Random(hash(f"{club.code}-members") % (2**31))
                shuffled_ids = all_student_ids[:]
                rng_local.shuffle(shuffled_ids)

                target_count = MEMBERS_PER_CLUB
                if club.membership_capacity:
                    target_count = min(target_count, club.membership_capacity)
                target_count = min(target_count, len(shuffled_ids))

                member_ids = shuffled_ids[:target_count]
                memberships = []

                for i, student_id in enumerate(member_ids):
                    membership, created = ClubMembership.objects.get_or_create(
                        club=club,
                        student_id=student_id,
                        defaults=dict(
                            status='active',
                            membership_number=f"{club.code}/{i + 1:04d}",
                            dues_paid=(club.annual_dues == 0),
                        ),
                    )
                    memberships.append(membership)
                    if created:
                        total_memberships += 1

                # Only assign leadership to members who are actually
                # 'active' — ClubLeadershipPosition.clean() requires this,
                # and a rerun might have fetched an existing but
                # non-active membership via get_or_create's get() branch.
                active_memberships = [m for m in memberships if m.status == 'active']

                for position, membership in zip(LEADERSHIP_POSITIONS_TO_SEED, active_memberships):
                    _, created = ClubLeadershipPosition.objects.get_or_create(
                        club=club,
                        position=position,
                        is_active=True,
                        defaults=dict(member=membership),
                    )
                    if created:
                        total_leadership += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✔ Seeded {total_memberships} membership(s), "
                f"{total_leadership} leadership position(s)."
            )
        )
