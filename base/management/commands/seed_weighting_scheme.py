# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_weighting_scheme
Usage: python manage.py seed_weighting_scheme

Seeds a single institution-wide default WeightingScheme (30% CAT / 70%
Exam — the standard split referenced elsewhere in this codebase, e.g.
Curriculum.weighting_scheme_override's docstring example). This is the
scheme Course.get_weighting_scheme() falls back to for any course that
doesn't specify its own, and what Curriculum.get_weighting_scheme()
falls back to for any curriculum slot without an override.

Idempotent: get_or_create keyed on `name`, so reruns don't duplicate.
Only ever creates ONE is_default=True scheme — WeightingScheme.clean()
enforces that at most one exists, and this command respects that by
checking for an existing default first rather than blindly creating.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction

from base.models import WeightingScheme, WeightingComponent

DEFAULT_SCHEME_NAME = "Standard 30/70"

# (result_type, weight_percent, aggregation, expected_count, best_n_count)
DEFAULT_COMPONENTS = [
    dict(
        result_type='C',
        weight_percent=Decimal('30.00'),
        aggregation=WeightingComponent.Aggregation.AVERAGE_ALL,
        expected_count=None,
        best_n_count=None,
    ),
    dict(
        result_type='E',
        weight_percent=Decimal('70.00'),
        aggregation=WeightingComponent.Aggregation.LATEST,
        expected_count=None,
        best_n_count=None,
    ),
]


class Command(BaseCommand):
    help = "Seed a single default WeightingScheme (30% CAT / 70% Exam) with its components"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the existing default scheme (and its components) before reseeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding default weighting scheme…"))

        existing_default = WeightingScheme.objects.filter(is_default=True).first()

        if options["reset"] and existing_default:
            name = existing_default.name
            existing_default.delete()  # cascades to its WeightingComponent rows
            self.stdout.write(self.style.WARNING(f"  --reset: deleted existing default scheme '{name}'."))
            existing_default = None

        if existing_default and existing_default.name != DEFAULT_SCHEME_NAME:
            # A default already exists under a different name — don't
            # silently create a second one; WeightingScheme.clean() would
            # reject it anyway (see the is_default uniqueness check), but
            # fail loudly here rather than letting get_or_create below
            # create a non-default duplicate scheme with the same target name.
            self.stderr.write(
                self.style.ERROR(
                    f"  A default WeightingScheme already exists: '{existing_default.name}'. "
                    f"Refusing to create a second one named '{DEFAULT_SCHEME_NAME}'. "
                    f"Re-run with --reset if you want to replace it."
                )
            )
            return

        with transaction.atomic():
            scheme, created = WeightingScheme.objects.get_or_create(
                name=DEFAULT_SCHEME_NAME,
                defaults=dict(is_default=True),
            )

            if not created and not scheme.is_default:
                # Scheme row already existed (e.g. from a partial prior
                # run) but wasn't flagged default yet — fix that now.
                scheme.is_default = True
                scheme.full_clean()
                scheme.save()

            component_count = 0
            for comp in DEFAULT_COMPONENTS:
                component, comp_created = WeightingComponent.objects.get_or_create(
                    scheme=scheme,
                    result_type=comp['result_type'],
                    defaults=dict(
                        weight_percent=comp['weight_percent'],
                        aggregation=comp['aggregation'],
                        expected_count=comp['expected_count'],
                        best_n_count=comp['best_n_count'],
                    ),
                )
                if comp_created:
                    component_count += 1

            try:
                scheme.validate_weights_sum_to_100()
            except ValidationError as e:
                self.stderr.write(self.style.ERROR(f"  ⚠ {e.messages[0]}"))
                return

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔  Default scheme ready: {scheme} "
                f"({'created' if created else 'already existed'}, "
                f"{component_count} new component(s))."
            )
        )
