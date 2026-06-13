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

from base.forms import ReportingForm
from base.models import (
    Reporting,
)
from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)


class ReportingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """
    Handles the student semester check-in / reporting registration process.

    This view manages both the rendering of the reporting status portal (GET)
    and the creation of a session reporting log upon successful form submission (POST).

    Access Control & Context Inheritance:
        - LoginRequiredMixin: Restricts access to authenticated portal accounts.
        - StudentProfileRequiredMixin: Ensures the logged-in user possesses an active Student profile.
        - StudentContextMixin: Provides helper access methods (`get_student`, `get_active_session`).

    Template:
        - `base/admissions/reporting.html`
    """

    login_url = config("LOGIN_URL") + '?next=admissions/reporting/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        """
            Renders the reporting portal layout.

            Evaluates check-in records to conditionally toggle dashboard action
            panels inside the template.
        """
        student = self.get_student(request)
        session = self.get_active_session()

        already_reported = Reporting.objects.filter(
            student=student,
            session=session
        ).first()

        if student and session:
            already_reported = Reporting.objects.filter(
                student=student, session=session
            ).exists()

        context = {
            'already_reported': already_reported,
            'session': session,
            'student': student
        }
        return render(request, 'base/admissions/reporting.html', context)

    def post(self, request):
        """
        Processes term check-in submissions.

        Validates form inputs and runs an idempotency query against the active 
        session to reject duplicate check-in requests with a 400 response.
        """

        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('No active session', status=400)

        if Reporting.objects.filter(student=student, session=session).exists():
            return HttpResponse('Already reported for this session', status=400)

        form = ReportingForm(request.POST)
        if form.is_valid():
            reporting = form.save(commit=False)
            reporting.student = student
            reporting.session = session
            reporting.save()
            return redirect('base-dashboard')

        context = {
            'form': form,
            'session': session,
        }
        return render(request, 'base/admissions/reporting.html', context)


class DefermentView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/defer/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        """Confirmation page before deferring"""
        context = {
            'student': self.get_student(request)
        }
        return render(request, 'base/admissions/defer.html', context)

    def post(self, request):
        student = self.get_student(request)
        if not student:
            return HttpResponse('Student not found', status=404)

        student.deffered = True
        # TODO :  add defer record here
        student.save()
        return redirect('base-dashboard')


class HostelBookingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/hostel/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        context = {
            'student': student,
            # 'current_hostel': student.hostel if student else None,
        }
        return render(request, 'base/admissions/hostel_booking.html', context)

    def post(self, request):
        student = self.get_student(request)
        hostel = request.POST.get('hostel')

        if not student or not hostel:
            return HttpResponse('Invalid request', status=400)

        student.stay = 'resident'
        student.save()
        return redirect('base-dashboard')
