# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Hall ticket domain — the exam admit card issued to a student for a
term (Session), verifiable via its serial number / QR payload.

This is the model `attendance.py`'s module docstring was referring to
when it noted the source's "Hall tickets & attendance" comment implied
a hall-ticket model that wasn't present yet — ExamCard is that model,
now split out on its own rather than folded into attendance.py, since
issuing a card (registrar-adjacent, term-scoped) and marking attendance
at a sitting (invigilation-adjacent, per-ExamSession) are different
points in the workflow with different owners.

Note ExamCard.session is the academic term (`Session`), not an
individual `ExamSession` sitting — one card covers every exam a
student sits that term, which is why both real imports below (Student,
Session) are needed rather than string FKs: the model queries/relates
through them directly elsewhere in the app, not just declaratively.

CIRCULAR-IMPORT RISK, CARRIED OVER FROM THE ORIGINAL: `from base.models
import Session` is a self-referential absolute import back into this
same top-level package. It only resolves if whatever module actually
defines `Session` (not among the files provided so far) finishes
importing into `base.models`'s namespace before `exams` does during
package init — otherwise this raises "cannot import name 'Session'
from partially initialized module 'base.models' (most likely due to a
circular import)". This was already a fragile absolute self-import in
the original flat file; splitting `models.py` into a real package makes
that fragility more likely to actually surface. Not changed here since
the safe fix — using a string `'Session'` FK the way the rest of this
codebase references not-yet-imported models — is a behavior-neutral
but still deliberate call, not a reshuffle.
"""

from django.db import models

from ..base import BaseModelMixin
from ..student import Student
from base.models import Session


class ExamCard(BaseModelMixin):
    """
    Represents an issued exam admit card for a student in a session.
    Serial number and QR payload are generated once and reused —
    regenerating creates a new ExamCard record (old one is superseded).

    A student can only have ONE active card per session — enforced as a
    partial unique constraint on is_active=True, NOT a plain
    unique_together on all three fields. A plain unique_together would
    also cap inactive rows at one per (student, session), which breaks
    the moment a student regenerates their card a second time (the
    deactivate step would try to insert a second (student, session,
    False) row and collide with the historical one from the first
    regeneration).
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='exam_cards'
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.PROTECT,
        related_name='exam_cards'
    )

    serial_number = models.CharField(max_length=30, unique=True)

    is_active = models.BooleanField(default=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    last_printed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'session'],
                condition=models.Q(is_active=True),
                name='unique_active_examcard_per_student_session',
            )
        ]
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.serial_number} — {self.student.registration_number} ({self.session})"

    @classmethod
    def generate_serial(cls):
        import random
        from datetime import datetime

        while True:
            year = datetime.now().year
            r1 = str(random.randint(0, 9999)).zfill(4)
            r2 = str(random.randint(0, 9999)).zfill(4)
            serial = f"UNI-{year}-{r1}-{r2}"
            if not cls.objects.filter(serial_number=serial).exists():
                return serial

    @property
    def qr_payload(self):
        return f"{self.student.registration_number}|{self.serial_number}|{self.session}"
