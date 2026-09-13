# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_hostel_listings
Usage: python manage.py seed_hostel_listings

Generates deterministic (replicable) seed data for HostelListing — the
off-campus hostel guide shown to students. Distinct from the on-campus
Hostel/Room/HostelAllocation models seeded by seed_academic_data.

Idempotent: uses get_or_create keyed on `name`, so reruns update nothing
and create nothing new for listings that already exist. Use --reset to
wipe and recreate every listing from scratch instead.
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import HostelListing

RNG = random.Random(42)

# ─────────────────────────────────────────────────────────────────────────────
# Static seed data
#
# Each row maps directly onto HostelListing's fields. Amenity booleans are
# picked deterministically per-listing below rather than hardcoded per row,
# so adding/removing listings doesn't require manually keeping 10 boolean
# columns in sync — see _amenities_for().
# ─────────────────────────────────────────────────────────────────────────────

LISTING_DATA = [
    dict(
        name="North Gate Residences",
        badge="popular",
        location="Along Thika Road, opposite North Gate",
        distance_note="2 min walk to North Gate",
        price_per_month=12000,
        room_type="single_ensuite",
        phone="+254712345001",
        email="info@northgateresidences.co.ke",
    ),
    dict(
        name="Scholars Court",
        badge="students",
        location="Juja Road, near the footbridge",
        distance_note="5 min walk to campus footbridge",
        price_per_month=8500,
        room_type="shared_2",
        phone="+254712345002",
        email="bookings@scholarscourt.co.ke",
    ),
    dict(
        name="Riverside Hostel",
        badge="scenic",
        location="Along the Ruiru riverbank, off Kimbo Road",
        distance_note="10 min walk, riverside path",
        price_per_month=9500,
        room_type="single",
        phone="+254712345003",
        email="riverside.hostel@gmail.com",
    ),
    dict(
        name="Unity Hall Annex",
        badge="community",
        location="Kimbo Estate, Block C",
        distance_note="15 min walk to South Gate",
        price_per_month=7000,
        room_type="shared_4",
        phone="+254712345004",
        email="unityhallannex@gmail.com",
    ),
    dict(
        name="Skyline Studios",
        badge="views",
        location="Ridgeways Road, 4th floor and up",
        distance_note="12 min walk, matatu route available",
        price_per_month=15000,
        room_type="studio",
        phone="+254712345005",
        email="hello@skylinestudios.co.ke",
    ),
    dict(
        name="Green Acres Lodge",
        badge=None,
        location="Off Kamiti Road, near the market",
        distance_note="8 min walk to campus, boda available",
        price_per_month=8000,
        room_type="mixed",
        phone="+254712345006",
        email="greenacreslodge@outlook.com",
    ),
    dict(
        name="Campus View Apartments",
        badge="popular",
        location="Thika Road Mall vicinity, Gate B",
        distance_note="3 min walk to Gate B",
        price_per_month=13500,
        room_type="single_ensuite",
        phone="+254712345007",
        email="campusview.apts@gmail.com",
    ),
    dict(
        name="Fellowship House",
        badge="community",
        location="Behind Ruiru Police Station",
        distance_note="20 min walk, shuttle stop nearby",
        price_per_month=6500,
        room_type="shared_4",
        phone="+254712345008",
        email="fellowshiphouse@gmail.com",
    ),
]

# Amenity flags this command can assign, each with a base probability of
# being True. Rolled per-listing with a listing-specific RNG (seeded off
# the listing's own name) so results are deterministic across reruns
# regardless of dict ordering.
AMENITY_CHANCES = {
    "has_wifi":         0.9,
    "has_meals":        0.35,
    "has_laundry":      0.5,
    "has_gym":          0.2,
    "has_parking":      0.4,
    "has_kitchen":      0.45,
    "has_study_rooms":  0.3,
    "has_lounge":       0.4,
    "has_bike_storage":  0.15,
    "has_ethernet":     0.25,
}

WIFI_NOTES = [
    "High-speed, WiFi + study rooms",
    "Fibre WiFi in every room",
    "WiFi included, backup generator",
    "",  # some listings just get the default "WiFi included" label
]


class Command(BaseCommand):
    help = "Seed deterministic off-campus HostelListing data for the student hostel guide"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing HostelListing rows before seeding fresh ones.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding hostel listings…"))

        if options["reset"]:
            deleted_count, _ = HostelListing.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  --reset: deleted {deleted_count} existing listing(s).")
            )

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for sort_order, row in enumerate(LISTING_DATA):
                amenities = self._amenities_for(row["name"])

                listing, created = HostelListing.objects.get_or_create(
                    name=row["name"],
                    defaults=dict(
                        badge=row["badge"],
                        location=row["location"],
                        distance_note=row["distance_note"],
                        price_per_month=row["price_per_month"],
                        room_type=row["room_type"],
                        phone=row["phone"],
                        email=row["email"],
                        is_published=True,
                        sort_order=sort_order,
                        **amenities,
                    ),
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  + {listing.name}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  = {listing.name} (already exists, left unchanged)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔  Seed complete. Created {created_count}, "
                f"skipped {updated_count} existing."
            )
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _amenities_for(self, listing_name):
        """
        Deterministically rolls amenity booleans + wifi_note for a listing,
        seeded off its name so the result is stable across reruns
        regardless of dict/iteration order.
        """
        rng_local = random.Random(hash(f"{listing_name}-amenities") % (2**31))

        amenities = {
            field: rng_local.random() < chance
            for field, chance in AMENITY_CHANCES.items()
        }

        # wifi_note only makes sense to set when has_wifi is True — otherwise
        # amenity_chips won't ever render it anyway (see the model property).
        if amenities["has_wifi"]:
            amenities["wifi_note"] = rng_local.choice(WIFI_NOTES)
        else:
            amenities["wifi_note"] = ""

        return amenities
