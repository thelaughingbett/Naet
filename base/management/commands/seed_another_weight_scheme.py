# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Management command: seed_weighting_scheme_cat_plus_exam
Usage: python manage.py seed_weighting_scheme_cat_plus_exam

Seeds a NON-default institution-wide WeightingScheme implementing the
"exam added to the average of CATs" policy.

Policy
------
The CAT average is the base score; the exam mark is contributed on top
of it. Per WeightingComponent.compute(), this is expressed by:

  * CAT component aggregates as AVERAGE_ALL across all CATs for the
    course, giving one CAT average.
  * Exam component aggregates as LATEST, giving the most recent exam
    mark, which is the value that gets added to the CAT average.

Weights still sum to exactly 100 to satisfy
WeightingScheme.validate_weights_sum_to_100(). The additive semantics
are a scoring-time concern (how the aggregated component scores are
combined), not a schema-level flag — see the model file for whether a
dedicated additive mode exists. If WeightingScheme later gains such a
field, add it to SCHEME_DEFAULTS below.

This scheme is deliberately NOT is_default=True: the 30/70 scheme from
seed_weighting_scheme is the single institution-wide default. This is
the alternate policy an institution opts into per-course / per-
curriculum via Course.weighting_scheme_override or
Curriculum.weighting_scheme_override.

Idempotent: get_or_create keyed on `name`.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import WeightingScheme, WeightingComponent

SCHEME_NAME = "CAT Average + Exam (added)"

# Scheme-level defaults. is_default stays False — there is already one
# default (the 30/70 scheme). Add a mode flag here if the model gains one.
SCHEME_DEFAULTS = {"is_default": False}

# (result_type, weight_percent, aggregation, expected_count, n_count)
#
# Field names match the actual WeightingComponent model in
# base/models/curriculum/grading_policy.py: it is `n_count`, NOT
# `best_n_count`.
COMPONENTS = [
    dict(
        result_type='C',
        weight_percent=Decimal('100.00'),
        aggregation=WeightingComponent.Aggregation.AVERAGE_ALL,
        expected_count=None,
        n_count=None,
    ),
    dict(
        result_type='E',
        weight_percent=Decimal('0.00'),
        aggregation=WeightingComponent.Aggregation.LATEST,
        expected_count=None,
        n_count=None,
    ),
]


class Command(BaseCommand):
    help = (
        "Seed the 'exam added to the average of CATs' weighting scheme "
        "(CAT average as base, exam mark added on top)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the existing scheme (and its components) before reseeding.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Create the scheme even if validate_weights_sum_to_100() "
                "or full_clean() rejects it. Use only if you know the "
                "model will accept it."
            ),
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Seeding weighting scheme: {SCHEME_NAME}…"
            )
        )

        existing = WeightingScheme.objects.filter(name=SCHEME_NAME).first()

        if options["reset"] and existing:
            existing.delete()  # cascades to its WeightingComponent rows
            self.stdout.write(
                self.style.WARNING(
                    f"  --reset: deleted existing scheme '{SCHEME_NAME}'.")
            )
            existing = None

        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f"  Scheme '{SCHEME_NAME}' already exists (pk={existing.pk}). "
                    f"Nothing to do — rerun with --reset to replace it."
                )
            )
            return

        with transaction.atomic():
            scheme, created = WeightingScheme.objects.get_or_create(
                name=SCHEME_NAME,
                defaults=SCHEME_DEFAULTS,
            )

            component_count = 0
            for comp in COMPONENTS:
                component, comp_created = WeightingComponent.objects.get_or_create(
                    scheme=scheme,
                    result_type=comp['result_type'],
                    defaults=dict(
                        weight_percent=comp['weight_percent'],
                        aggregation=comp['aggregation'],
                        expected_count=comp['expected_count'],
                        n_count=comp['n_count'],
                    ),
                )
                if comp_created:
                    component_count += 1

            try:
                scheme.full_clean()
                scheme.validate_weights_sum_to_100()
            except ValidationError as e:
                if not options["force"]:
                    transaction.set_rollback(True)
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ⚠ {e.messages[0] if e.messages else e}\n"
                            f"  The 'CAT average + exam' split was rejected by "
                            f"WeightingScheme validation. If your model has a "
                            f"dedicated additive mode, wire it into "
                            f"SCHEME_DEFAULTS and/or the component weights, then "
                            f"rerun with --force."
                        )
                    )
                    return
                self.stdout.write(
                    self.style.WARNING(
                        f"  --force: created scheme despite validation warning: "
                        f"{e.messages[0] if e.messages else e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔  Scheme ready: {scheme} "
                f"({'created' if created else 'already existed'}, "
                f"{component_count} new component(s))."
            )
        )
