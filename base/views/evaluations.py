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
    HostelAllocation,
    HostelEvaluation
)

from .base import (
    StudentContextMixin,
    StudentProfileRequiredMixin
)


class CourseEvaluationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/course/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled_courses = student.enrollments.filter(
            session=session
        ).select_related('course') if student and session else []

        curricula = Curriculum.objects.filter(
            session=session,
            Tclass=student.class_entered
        )
        context = {
            'curricula': curricula,
            'courses': enrolled_courses,
            'student': student,
        }
        return render(request, 'base/evaluations/course.html', context)


class LecturerEvaluationView(
    LoginRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/lecturer/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        # Fetch Curriculum instances with prefetched relationships
        curricula = Curriculum.objects.filter(
            Tclass=student.class_entered,
            session=session
        ).select_related(
            'course'
        ).prefetch_related(
            'professor__user'
        ) if student and session else []

        context = {
            'curricula': curricula,
            'student': student,
        }
        return render(request, 'base/evaluations/lecturer.html', context)


class HostelEvaluationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/hostel/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()
        # TODO : check if hostel records exist else redirect to referer

        try:
            allocation = HostelAllocation.objects.get(
                student=student,
                session=session
            )

            try:
                evaluation = HostelEvaluation.objects.get(
                    allocation=allocation)
            except:
                evaluation = None

        except:
            allocation = None

        context = {
            'allocation': allocation,
            'student': student,
            'evaluation': evaluation
        }
        return render(request, 'base/evaluations/hostel.html', context)
