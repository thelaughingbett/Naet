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

from django.db import models

from .base import (
    BaseModelMixin,

    id_type_choices,
)


class ParentGuardian(BaseModelMixin):
    RELATION_CHOICES = [
        ('father',   'Father'),
        ('mother',   'Mother'),
        ('guardian', 'Guardian'),
    ]

    student = models.ForeignKey(
        'Student', on_delete=models.CASCADE, related_name='parents')
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    name = models.CharField(max_length=255)
    id_type = models.CharField(max_length=24, choices=id_type_choices)
    id_no = models.CharField(max_length=34)
    date_of_birth = models.DateField()


class EmergencyContact(BaseModelMixin):
    RELATIONSHIP_CHOICES = [
        ('father',        'Father'),
        ('mother',        'Mother'),
        ('guardian',      'Guardian'),
        ('spouse',        'Spouse'),
        ('child',         'Child'),
        ('sibling',       'Sibling'),
        ('grandparent',   'Grandparent'),
        ('grandchild',    'Grandchild'),
        ('relative',      'Relative'),
        ('coworker',      'Coworker'),
        ('neighbor',      'Neighbor'),
        ('caregiver',     'Caregiver'),
        ('family-friend', 'Family Friend'),
        ('friend',        'Friend'),
        ('other',         'Other'),
    ]

    student = models.ForeignKey(
        'Student', on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=78)
    phone = models.CharField(max_length=78)
    email = models.CharField(max_length=78)
    relationship = models.CharField(
        max_length=78, choices=RELATIONSHIP_CHOICES)
    address = models.CharField(max_length=78, null=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_primary_contact_per_student'
            )
        ]
