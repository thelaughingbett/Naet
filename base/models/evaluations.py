# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import BaseModelMixin
from django.db import models


class CourseEvaluation(BaseModelMixin):
    enrollment = models.OneToOneField(
        "Enrollment",
        on_delete=models.CASCADE,
        related_name="evaluation"
    )

    rating = models.IntegerField(default=0)
    comments = models.TextField(blank=True, null=True)


class LecturerEvaluation(BaseModelMixin):
    enrollment = models.ForeignKey(
        "Enrollment",
        on_delete=models.CASCADE,
        related_name="lecturer_evaluations"
    )

    lecturer = models.ForeignKey(
        "Lecturer",
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(default=0)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('enrollment', 'lecturer')


HOSTEL_EVALUATION_CATEGORIES = [
    ('cleanliness',  'Cleanliness'),
    ('security',     'Security'),
    ('water_supply', 'Water Supply'),
    ('electricity',  'Electricity & Power'),
    ('noise_levels', 'Noise Levels'),
    ('maintenance',  'Maintenance & Repairs'),
]

_RATING_CHOICES = [(i, i) for i in range(1, 6)]


class HostelEvaluation(BaseModelMixin):
    """
    One evaluation per HostelAllocation — i.e. one per student per session
    they were resident. Category field names are derived from
    HOSTEL_EVALUATION_CATEGORIES (<key>_rating), so the view can build
    kwargs for create() generically.
    """
    allocation = models.OneToOneField(
        'HostelAllocation',
        on_delete=models.CASCADE,
        related_name='evaluation'
    )

    cleanliness_rating = models.IntegerField(choices=_RATING_CHOICES)
    security_rating = models.IntegerField(choices=_RATING_CHOICES)
    water_supply_rating = models.IntegerField(choices=_RATING_CHOICES)
    electricity_rating = models.IntegerField(choices=_RATING_CHOICES)
    noise_levels_rating = models.IntegerField(choices=_RATING_CHOICES)
    maintenance_rating = models.IntegerField(choices=_RATING_CHOICES)

    rating = models.IntegerField(choices=_RATING_CHOICES)  # overall
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"Evaluation for {self.allocation}"
