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
    Curriculum,
    Session,
)


from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)


class CurriculumView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/curriculum/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()
        # TODO : add sessions

        curriculum = Curriculum.objects.none()
        if student and session:
            curriculum = Curriculum.objects.filter(
                Tclass=student.class_entered
            ).select_related('course', 'session').prefetch_related('professor')

        target_class = student.class_entered

        # 1. Find the earliest session this class was ever a part of
        earliest_session = Session.objects.filter(
            curriculum__Tclass=target_class
        ).order_by('start_date').first()

        if not earliest_session:
            sessions = Session.objects.none()  # Return empty if class has no history
        else:
            # 2. Grab every session from that start date up until the current timeline
            sessions = Session.objects.filter(
                start_date__gte=earliest_session.start_date
            ).order_by('start_date')

        context = {
            'curriculum': curriculum,
            'session': session,
            'student': student,
            'sessions': sessions
        }

        return render(request, 'base/academics/curriculum.html', context)


class UnitRegistrationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/units/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled_ids = student.enrollments.values_list(
            'record_id', flat=True
        ) if student else []

        available = Curriculum.objects.none()
        if student and session:
            available = Curriculum.objects.filter(
                Tclass=student.class_entered,
                session=session,
                # course__type='E'  # electives only — core auto-enrolled
            ).exclude(
                record_id__in=enrolled_ids
            ).select_related('course')

        context = {
            'available': available,
            'enrolled': student.enrollments.filter(
                session=session
            ).select_related('course') if student and session else [],
            'student': student,
            'session': session,
        }
        return render(request, 'base/academics/unit_registration.html', context)

    def post(self, request):
        """Enroll in a selected elective"""
        student = self.get_student(request)
        session = self.get_active_session()
        curriculum_id = request.POST.get('curriculum_id')

        if not all([student, session, curriculum_id]):
            return HttpResponse('Invalid request', status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id,
                Tclass=student.class_entered,
                session=session,
                course__type='E'
            )
            # student.enrollments.add(curriculum)
            # TODO : create enrollment here
            # TODO : make transaction atomic
        except Curriculum.DoesNotExist:
            return HttpResponse('Unit not found', status=404)

        return render(request, 'base/academics/unit_registration.html', {
            'message': 'Enrolled successfully'
        })


class ResultsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/results/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        from base.models import Result
        student = self.get_student(request)
        session = self.get_active_session()

        results = Result.objects.none()
        if student:
            target_class = student.class_entered

            # 1. Find the earliest session this class was ever a part of
            earliest_session = Session.objects.filter(
                curriculum__Tclass=target_class
            ).order_by('start_date').first()

            if not earliest_session:
                sessions = Session.objects.none()  # Return empty if class has no history
            else:
                # 2. Grab every session from that start date up until the current timeline
                sessions = Session.objects.filter(
                    start_date__gte=earliest_session.start_date
                ).order_by('start_date')
                results = Result.objects.filter(
                    student=student
                ).select_related('curricula__course').order_by('-created_at')

        context = {
            'results': results,
            'student': student,
            'session': session,
            'sessions': sessions
        }
        return render(request, 'base/academics/results.html', context)
