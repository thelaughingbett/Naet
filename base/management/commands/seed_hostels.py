# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_hostels
Usage: python manage.py seed_hostels

Seeds Hostel + Room rows deterministically, then allocates a capped,
deterministic slice of students to rooms for the active session —
respecting HostelAllocation.clean()'s gender-matching and capacity
rules (a mixed-gender hostel accepts anyone; a single-gender hostel
only accepts a matching student.user.gender).

Idempotent: get_or_create throughout, so reruns don't duplicate.
Allocations are capped by MAX_RESIDENTS and picked via a
student-seeded RNG shuffle, so reruns against the same DB land on the
same residents.
"""

import random

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction

from base.models import Hostel, Room, HostelAllocation, Session, Student

# (name, gender, num_rooms, room_type, capacity_per_room, price_per_semester)
HOSTEL_DATA = [
    dict(name="Newton Hall", gender="M", num_rooms=20,
         room_type="double", capacity=2, price=12000),
    dict(name="Curie Hall", gender="F", num_rooms=20,
         room_type="double", capacity=2, price=12000),
    dict(name="Mandela Court", gender="mixed", num_rooms=10,
         room_type="ensuite", capacity=1, price=22000),
    dict(name="Kenyatta Wing", gender="M", num_rooms=15,
         room_type="triple", capacity=3, price=9000),
    dict(name="Wangari Wing", gender="F", num_rooms=15,
         room_type="triple", capacity=3, price=9000),
]

# Cap total residents seeded, regardless of how many students exist —
# keeps the dataset small and easy to inspect, same convention used by
# seed_academic_data's own hostel step.
MAX_RESIDENTS = 60

# Fraction of eligible (gender-matched, non-full-room) students who get
# an allocation attempt at all — not every student is a resident.
RESIDENT_SELECTION_CHANCE = 0.35

# Allocation status outcomes, in order — first match wins.
STATUS_WEIGHTS = [
    ('APPROVED', 0.75),
    ('PENDING', 0.15),
    ('REJECTED', 0.10),
]


class Command(BaseCommand):
    help = "Seed Hostel, Room, and HostelAllocation data for the active session"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing HostelAllocation, Room, and Hostel rows before seeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding hostels…"))

        if options["reset"]:
            deleted_allocs, _ = HostelAllocation.objects.all().delete()
            deleted_rooms, _ = Room.objects.all().delete()
            deleted_hostels, _ = Hostel.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"  --reset: deleted {deleted_allocs} allocation(s), "
                f"{deleted_rooms} room(s), {deleted_hostels} hostel(s)."
            ))

        active_session = Session.objects.filter(is_active=True).first()
        if not active_session:
            self.stderr.write(self.style.ERROR(
                "  No active Session found — run seed_academic_data first."
            ))
            return

        hostels_created = 0
        rooms_created = 0

        with transaction.atomic():
            all_rooms_by_gender = {}

            for h in HOSTEL_DATA:
                hostel, created = Hostel.objects.get_or_create(
                    name=h["name"],
                    defaults=dict(gender=h["gender"], is_active=True),
                )
                if created:
                    hostels_created += 1

                rooms = []
                for i in range(1, h["num_rooms"] + 1):
                    room, r_created = Room.objects.get_or_create(
                        hostel=hostel,
                        room_number=f"{i:03d}",
                        defaults=dict(
                            room_type=h["room_type"],
                            capacity=h["capacity"],
                            floor=(i - 1) // 10 + 1,
                            price_per_semester=h["price"],
                            is_active=True,
                        ),
                    )
                    rooms.append(room)
                    if r_created:
                        rooms_created += 1

                all_rooms_by_gender.setdefault(h["gender"], []).extend(rooms)
                self.stdout.write(
                    f"  Hostel: {hostel.name} ({hostel.gender}) — "
                    f"{len(rooms)} rooms × {h['capacity']} beds"
                )

        self.stdout.write(
            f"\n  ✔ {hostels_created} new hostel(s), {rooms_created} new room(s)."
        )

        allocations_created = self._seed_allocations(
            active_session, all_rooms_by_gender
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n✔  Seed complete. {allocations_created} allocation(s) created "
            f"for {active_session}."
        ))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _pick_room(self, student, rooms_by_gender):
        """
        Returns a non-full room matching this student's gender, or a
        mixed-gender room, or None if nothing's available. Mirrors
        HostelAllocation.clean()'s own gender rule so we never attempt
        an allocation clean() would reject.
        """
        candidates = (
            rooms_by_gender.get(student.user.gender, [])
            + rooms_by_gender.get('mixed', [])
        )
        rng_local = random.Random(
            hash(f"{student.registration_number}-room-pick") % (2**31)
        )
        rng_local.shuffle(candidates)
        return next((r for r in candidates if not r.is_full), None)

    def _pick_status(self, student):
        rng_local = random.Random(
            hash(f"{student.registration_number}-alloc-status") % (2**31)
        )
        roll = rng_local.random()
        cumulative = 0.0
        for status, weight in STATUS_WEIGHTS:
            cumulative += weight
            if roll < cumulative:
                return status
        return STATUS_WEIGHTS[-1][0]

    def _seed_allocations(self, session, rooms_by_gender):
        students = list(Student.objects.select_related('user').all())
        if not students:
            self.stdout.write(self.style.WARNING(
                "  ⚠ No Student rows found — skipped allocations. "
                "Run seed_academic_data first."
            ))
            return 0

        rng_order = random.Random(hash(f"{session.record_id}-order") % (2**31))
        rng_order.shuffle(students)

        created_count = 0

        with transaction.atomic():
            for student in students:
                if created_count >= MAX_RESIDENTS:
                    break

                # Skip students who already have an allocation this
                # session — unique_together('student', 'session') would
                # reject a second one anyway, but this avoids the wasted
                # clean()/save() round trip on reruns.
                if HostelAllocation.objects.filter(
                    student=student, session=session
                ).exists():
                    continue

                rng_local = random.Random(
                    hash(f"{student.registration_number}-selected") % (2**31)
                )
                if rng_local.random() >= RESIDENT_SELECTION_CHANCE:
                    continue

                room = self._pick_room(student, rooms_by_gender)
                if not room:
                    continue  # no eligible non-full room for this student's gender

                status = self._pick_status(student)

                allocation = HostelAllocation(
                    student=student,
                    room=room,
                    session=session,
                    status=status,
                    allocated_by='SYSTEM',
                    move_in_date=session.start_date,
                )

                try:
                    allocation.full_clean()
                    allocation.save()
                    created_count += 1
                except ValidationError as e:
                    # Shouldn't normally trigger given _pick_room already
                    # respects gender/capacity, but don't let one bad
                    # pick abort the whole seed run.
                    self.stdout.write(self.style.WARNING(
                        f"  ! Skipped {student.registration_number}: {e.messages}"
                    ))
                    continue

        return created_count
