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

from base.models import Payment
from django.views.decorators.cache import never_cache
from django.contrib import messages

from http import HTTPStatus
import logging

from decouple import config

from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.views.generic import (
    DetailView,
    ListView,
    DeleteView
)
from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.db import (
    DatabaseError,
    IntegrityError,
    transaction
)
from django.utils.http import url_has_allowed_host_and_scheme

from base.models import (
    Timetable,
    ExamSession,
    Session
)

from .base import (
    StudentContextMixin,
    StudentProfileRequiredMixin
)


class WeeklyScheduleView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=timetable/schedule/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI']

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        timetable = []
        has_slots = False

        if student and session:
            entries = Timetable.objects.filter(
                curriculum__Tclass=student.class_entered,
                curriculum__session=session,
            ).select_related(
                'curriculum__course',
                'curriculum__Tclass',
                'venue',
            ).prefetch_related(
                'curriculum__professor__user'
            ).order_by('time_slot')

            has_slots = entries.exists()

            # build lookup: {(time_slot, day): entry}
            grid = {
                (e.time_slot, e.day): e
                for e in entries
            }

            # use TIME_SLOTS from the model directly
            for slot_value, slot_label in Timetable.TIME_SLOTS:
                row = {
                    'value': slot_value,   # '08:00-10:00'
                    'label': slot_label,   # '1st Slot (08:00 - 10:00)'
                    'days': {
                        day: grid.get((slot_value, day))
                        for day in self.DAYS
                    }
                }
                timetable.append(row)

        return render(request, 'base/timetable/weekly_schedule.html', {
            'timetable':  timetable,
            'has_slots':  has_slots,
            'days':       self.DAYS,
            'student':    student,
            'session':    session,
        })


class ExamTimetableView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=timetable/exams/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        exam_sessions = ExamSession.objects.filter(
            curriculum__Tclass=student.class_entered,
            curriculum__session=session,
        ).select_related(
            'curriculum__course',
            'curriculum__session',
        ).prefetch_related(
            'venues__venue',
            'venues__invigilator__user',
        ).order_by('date', 'time_slot') if session else []

        all_sessions = Session.objects.filter(
            curricula__exam_sessions__isnull=False
        ).distinct().order_by('-academic_year', '-semester')

        return render(request, 'base/timetable/exam.html', {
            'student':       student,
            'session':       session,
            'exam_sessions': exam_sessions,
            'all_sessions':  all_sessions,
        })
