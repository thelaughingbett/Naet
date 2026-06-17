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


class Hostel(BaseModelMixin):
    """
    A physical hostel building on campus.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('mixed', 'Mixed'),
    ]

    name = models.CharField(max_length=78)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    # school = models.ForeignKey(
    #     'School',
    #     on_delete=models.PROTECT,
    #     related_name='hostels'
    # )
    warden = models.ForeignKey(
        'HostelWarden',  # or User
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_hostels'
    )
    # is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def total_capacity(self):
        return self.rooms.aggregate(
            total=models.Sum('capacity')
        )['total'] or 0

    @property
    def occupied_beds(self):
        return HostelAllocation.objects.filter(
            room__hostel=self,
            is_active=True
        ).count()

    @property
    def available_beds(self):
        return self.total_capacity - self.occupied_beds


class Room(BaseModelMixin):
    """
    An individual room within a hostel.
    """
    ROOM_TYPE_CHOICES = [
        ('single',  'Single'),
        ('double',  'Double'),
        ('triple',  'Triple'),
        ('ensuite', 'En-suite'),
    ]

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.PROTECT,
        related_name='rooms'
    )
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES)
    capacity = models.IntegerField(default=2)
    floor = models.IntegerField(default=1)
    # is_active = models.BooleanField(default=True)
    price_per_semester = models.PositiveIntegerField(default=0)  # KES

    class Meta:
        unique_together = ('hostel', 'room_number')

    def __str__(self):
        return f"{self.hostel.name} — Room {self.room_number}"

    @property
    def is_full(self):
        return HostelAllocation.objects.filter(
            room=self, is_active=True
        ).count() >= self.capacity

    @property
    def occupants(self):
        return HostelAllocation.objects.filter(
            room=self, is_active=True
        ).select_related('student__user')


class HostelAllocation(BaseModelMixin):
    """
    Links a student to a specific room for a specific session.
    Replaces student.hostel CharField.
    """
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='hostel_allocations'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='allocations'
    )
    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='hostel_allocations'
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    move_in_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        # one room slot per student per session
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student} → {self.room} ({self.session})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.room.is_full:
            raise ValidationError(
                f"Room {self.room} is at full capacity."
            )
        # gender check
        student_gender = self.student.user.gender
        hostel_gender = self.room.hostel.gender
        if hostel_gender != 'mixed' and student_gender != hostel_gender:
            raise ValidationError(
                f"{self.room.hostel.name} does not accommodate {student_gender} students."
            )
