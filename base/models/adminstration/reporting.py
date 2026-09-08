# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


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
