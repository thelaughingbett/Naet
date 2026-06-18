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

from simple_history.models import HistoricalRecords


from django.db import models
from simple_history.models import HistoricalRecords


class DefermentDocument(BaseModelMixin):
    """
    Supporting document uploaded alongside a deferment request.
    One deferment can have multiple attachments.
    """
    deferment = models.ForeignKey(
        'Deferment',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='deferments/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_name} → {self.deferment}"


class Deferment(BaseModelMixin):
    """
    Records each individual deferment event for a student.
    A student may defer multiple times — each gets its own record.
    """

    REASON_CHOICES = [
        ('financial',   'Financial Difficulty'),
        ('medical',     'Medical'),
        ('personal',    'Personal'),
        ('academic',    'Academic'),
        ('other',       'Other'),
    ]

    STATUS_CHOICES = [
        ('active',      'Active'),
        ('reinstated',  'Reinstated'),
        ('withdrawn',   'Withdrawn'),
    ]

    # Approval workflow — separate from the deferment status itself
    REQUEST_STATUS_CHOICES = [
        ('pending',   'Pending Review'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='deferments'
    )
    session_deferred = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='deferments',
        help_text='The session the student deferred from'
    )
    session_returning = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='returning_students',
        null=True,
        blank=True,
        help_text='The session the student is expected to return'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='personal'
    )
    reason_detail = models.TextField(
        null=True,
        blank=True,
        help_text='Free text from student or registrar'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )
    request_status = models.CharField(
        max_length=10,
        choices=REQUEST_STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='approved_deferments',
        null=True,
        blank=True,
    )
    reinstated_at = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"


class Reporting(BaseModelMixin):

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='reportings',
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name='reportings'
    )

    REPORTED_VIA_CHOICES = [
        ("online", "Online"),
        ("physical", "Physical")
    ]

    reported_at = models.DateTimeField(
        auto_now_add=True
    )

    reported_via = models.CharField(
        max_length=10,
        choices=REPORTED_VIA_CHOICES
    )

    history = HistoricalRecords()

    class Meta:
        # can't report twice in same session
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student} - {self.session}"


class HostelListing(BaseModelMixin):
    """
    External hostel listing for the student hostel guide.
    These are off-campus options — not the same as the Hostel model
    which tracks on-campus rooms and allocations.
    """

    BADGE_CHOICES = [
        ('popular',   '⭐ Popular'),
        ('students',  '👩‍🎓 Students only'),
        ('scenic',    '🏞️ Scenic'),
        ('community', '🤝 Community'),
        ('views',     '🌅 Great views'),
        ('other',     'Other'),
    ]

    ROOM_TYPE_CHOICES = [
        ('single',         'Single'),
        ('single_ensuite', 'Single en-suite'),
        ('shared_2',       '2–4 sharing'),
        ('shared_4',       '4–6 sharing'),
        ('studio',         'Studio & shared'),
        ('mixed',          'Single & shared'),
    ]

    name = models.CharField(max_length=120)
    badge = models.CharField(
        max_length=20, choices=BADGE_CHOICES, null=True, blank=True)
    location = models.CharField(
        max_length=255, help_text='Street address and landmark')
    distance_note = models.CharField(
        max_length=120, help_text='e.g. 2 min walk to North Gate')

    price_per_month = models.PositiveIntegerField(help_text='KES per month')
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)

    # amenity toggles — rendered as chips in the template
    has_wifi = models.BooleanField(default=True)
    has_meals = models.BooleanField(default=False)
    has_laundry = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_kitchen = models.BooleanField(default=False)
    has_study_rooms = models.BooleanField(default=False)
    has_lounge = models.BooleanField(default=False)
    has_bike_storage = models.BooleanField(default=False)
    has_ethernet = models.BooleanField(default=False)
    wifi_note = models.CharField(
        max_length=60, blank=True, help_text='e.g. High-speed, WiFi + study rooms')

    phone = models.CharField(max_length=20)
    email = models.EmailField()

    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(
        default=0, help_text='Lower = appears first')

    class Meta:
        ordering = ['sort_order', 'price_per_month']

    def __str__(self):
        return self.name

    @property
    def amenity_chips(self):
        """Returns a list of (icon, label) tuples for template rendering."""
        chips = []
        wifi_label = self.wifi_note or 'WiFi included'
        if self.has_wifi:
            chips.append(('📶', wifi_label))
        if self.has_meals:
            chips.append(('🍽️', 'Meal plan optional'))
        if self.has_laundry:
            chips.append(('🧺', 'Laundry on site'))
        if self.has_gym:
            chips.append(('🏋️', 'Gym access'))
        if self.has_parking:
            chips.append(('🅿️', 'Free parking'))
        if self.has_kitchen:
            chips.append(('🍳', 'Kitchen access'))
        if self.has_study_rooms:
            chips.append(('📚', 'Study rooms'))
        if self.has_lounge:
            chips.append(('🎮', 'Common lounge'))
        if self.has_bike_storage:
            chips.append(('🚲', 'Bike storage'))
        if self.has_ethernet:
            chips.append(('🔌', 'WiFi + ethernet'))
        return chips
