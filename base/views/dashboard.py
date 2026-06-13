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

from django.contrib import messages

from http import HTTPStatus

from decouple import config

from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)
from django.urls import reverse
from django.views import View

from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)

from django.db import (
    DatabaseError,
    IntegrityError,
    transaction
)
from django.utils.http import url_has_allowed_host_and_scheme

from base.models import (
    Curriculum,
    StudentFeeAccount,

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

        student = self.get_student(request)
        session = self.get_active_session()

        fee_account = StudentFeeAccount.objects.filter(
            student=student
        ).order_by('-created_at').last()

        enrollments = Curriculum.objects.none()
        fee_balance = None
        session_progress = 0

        if student and session:
            enrollments = student.enrollments.filter(
                session=session
            ).select_related('course')[:5]

            try:
                account = StudentFeeAccount.objects.get(
                    student=student,
                    fee_structure__session=session
                )

                fee_balance = account.balance
            except StudentFeeAccount.DoesNotExist:
                fee_balance = 0.0

            if session.start_date and session.end_date:
                from django.utils import timezone
                today = timezone.now().date()
                total = (session.end_date - session.start_date).days
                elapsed = (today - session.start_date).days
                session_progress = min(
                    100, round((elapsed / total) * 100)
                ) if total > 0 else 0

        context = {
            'user': request.user,
            'fee_account': fee_account,
            'session': session,
            'student': student,
            'session': session,
            'enrollments': enrollments,
            'fee_balance': fee_balance,
            'session_progress': session_progress,
            'year': __import__('datetime').date.today().year,
        }
        return render(request, 'base/index.html', context)
