# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Seeds the standard A/B/C/D/E grading scale as the institution default.

    python manage.py seed_grading_scale
    python manage.py seed_grading_scale --name "Undergraduate standard"
    python manage.py seed_grading_scale --not-default

Idempotent: re-running it updates existing bands to match the table
below rather than erroring on the unique_together('scale', 'min_score')
constraint, so it's safe to put in a deploy step.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import GradingScale, GradingBand

DEFAULT_SCALE_NAME = "Undergraduate standard"

# Mirrors the SCORE_TO_GRADE_POINTS constant this replaces.
BANDS = [
    (70, 4.0, 'A'),
    (60, 3.0, 'B'),
    (50, 2.0, 'C'),
    (40, 1.0, 'D'),
    (0, 0.0, 'E'),
]


class Command(BaseCommand):
    help = "Seeds a GradingScale with the standard A/B/C/D/E bands."

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            default=DEFAULT_SCALE_NAME,
            help=f"Name for the scale (default: '{DEFAULT_SCALE_NAME}').",
        )
        parser.add_argument(
            '--not-default',
            action='store_true',
            help="Don't mark this scale as the institution default "
                 "(is_default=True). Use this if you're seeding an "
                 "additional scale, e.g. for postgraduate thesis courses.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        name = options['name']
        make_default = not options['not_default']

        if make_default:
            # Unset any existing default first — GradingScale.clean() only
            # blocks a *second* is_default=True from being saved, it won't
            # silently steal the flag from an existing scale for us.
            existing_default = GradingScale.objects.filter(
                is_default=True
            ).exclude(name=name).first()
            if existing_default:
                existing_default.is_default = False
                existing_default.full_clean()
                existing_default.save(update_fields=['is_default'])
                self.stdout.write(
                    f"Unset is_default on existing scale '{existing_default.name}'."
                )

        scale, created = GradingScale.objects.get_or_create(
            name=name,
            defaults={'is_default': make_default},
        )
        if not created and scale.is_default != make_default:
            scale.is_default = make_default
            scale.full_clean()
            scale.save(update_fields=['is_default'])

        for min_score, points, label in BANDS:
            band, band_created = GradingBand.objects.update_or_create(
                scale=scale,
                min_score=min_score,
                defaults={'grade_points': points, 'label': label},
            )
            verb = "Created" if band_created else "Updated"
            self.stdout.write(f"  {verb} band: {band}")

        self.stdout.write(self.style.SUCCESS(
            f"Grading scale '{scale.name}' seeded"
            f"{' as institution default' if scale.is_default else ''}."
        ))
