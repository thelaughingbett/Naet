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

from decouple import config

from django.shortcuts import (
    render,
)
from django.urls import reverse
from django.views import View

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)

from base.models import (
    Curriculum,
    StudentFeeAccount,
    Timetable
)
from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)


class IndexView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        import datetime

        student = self.get_student(request)
        session = self.get_active_session()

        fee_account = None
        fee_balance = None
        enrollments = Curriculum.objects.none()
        today_slots = []
        deadlines = []

        if student and session:

            # fee account
            fee_account = StudentFeeAccount.objects.filter(
                student=student,
                fee_structure__session=session,
            ).select_related('fee_structure__session').first()

            fee_balance = fee_account.balance if fee_account else None

            # enrollments — approved only, limit 5 for dashboard
            enrollments = Curriculum.objects.filter(
                enrollment_records__student=student,
                enrollment_records__status='approved',
                session=session,
            ).select_related('course')[:5]

            # today's timetable
            today = datetime.date.today()
            day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI'}
            today_day = day_map.get(today.weekday())

            if today_day:
                entries = Timetable.objects.filter(
                    curriculum__session=session,
                    curriculum__Tclass=student.class_entered,
                    day=today_day,
                ).select_related(
                    'curriculum__course',
                    'venue',
                ).prefetch_related(
                    'curriculum__professor__user'
                ).order_by('time_slot')

                # build lookup: {'08:00-10:00': entry}
                entry_map = {e.time_slot: e for e in entries}

                # build slot list using model's TIME_SLOTS
                today_slots = [
                    {
                        'label': label,     # '1st Slot (08:00 - 10:00)'
                        'value': value,     # '08:00-10:00'
                        'entry': entry_map.get(value),
                    }
                    for value, label in Timetable.TIME_SLOTS
                ]

            # deadlines
            # TODO :  once  connected to lms add assignments deadlines
            # TODO :  support clubs and add club deadlines
            if fee_account and not fee_account.is_cleared:
                due = fee_account.days_remaining
                days_left = (due - today).days
                deadlines.append({
                    'label':     'Fee payment deadline',
                    'display':   f'{days_left} days left' if days_left <= 7 else due.strftime('%b %d, %Y'),
                    'is_urgent': days_left <= 7,
                })

        return render(request, 'base/index.html', {
            'user':              request.user,
            'student':           student,
            'session':           session,
            'fee_account':       fee_account,
            'fee_balance':       fee_balance,
            'enrollments':       enrollments,
            'today_slots':       today_slots,
            'deadlines':         deadlines,
            'year':              datetime.date.today().year,
        })
