# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Exam attendance domain — whether a student actually sat an ExamSession,
and any malpractice reported during it.

Split out on its own rather than folded into results-admin: attendance
is recorded by invigilation staff at the exam venue, independently of
and typically before grading/results processing touches the sitting.

NOTE: the module comment in the original source ("Hall tickets &
attendance") implies a hall-ticket model was planned alongside this,
but only ExamAttendance exists in the source provided — nothing to
split out for hall tickets yet.
"""

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


class ExamAttendance(BaseModelMixin):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        MALPRACTICE = "malpractice", "Malpractice Reported"

    exam_session = models.OneToOneField(
        "ExamSession",
        on_delete=models.CASCADE,
        related_name="attendance"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABSENT
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    remarks = models.TextField(blank=True)
