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

from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import (
    render,
    redirect
)
from django.views import View
from django.contrib.auth.mixins import (
    LoginRequiredMixin,

)
from base.models import (
    Curriculum,
    HostelAllocation,
    HostelEvaluation,
    CourseEvaluation,
    Enrollment,
    LecturerEvaluation,
    HOSTEL_EVALUATION_CATEGORIES
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

        enrollments = []
        if student and session:
            enrollments = list(
                Enrollment.objects
                .filter(
                    student=student,
                    curriculum__session=session,
                    status='approved',
                )
                .select_related('curriculum__course')
                .prefetch_related('curriculum__professor')
            )

        if enrollments:
            evaluations = CourseEvaluation.objects.filter(
                enrollment__in=enrollments
            )
            evaluation_by_enrollment = {
                ev.enrollment_id: ev for ev in evaluations
            }
            for enrollment in enrollments:
                enrollment.submitted_evaluation = evaluation_by_enrollment.get(
                    enrollment.pk)

        context = {
            'enrollments': enrollments,
            'student': student,
            'session': session,
        }
        return render(request, 'base/evaluations/course.html', context)

    def post(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('Invalid request', status=400)

        enrollment_id = request.POST.get('enrollment_id')
        rating_raw = request.POST.get('rating')
        comments = request.POST.get('comments', '').strip()

        if not enrollment_id or not rating_raw:
            return HttpResponse('Rating is required', status=400)

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            return HttpResponse('Invalid rating', status=400)

        if rating < 1 or rating > 5:
            return HttpResponse('Rating must be between 1 and 5', status=400)

        enrollment = (
            Enrollment.objects
            .filter(
                record_id=enrollment_id,
                student=student,
                curriculum__session=session,
            )
            .first()
        )
        if not enrollment:
            return HttpResponse('Enrollment not found', status=404)

        if CourseEvaluation.objects.filter(enrollment=enrollment).exists():
            return HttpResponse('You have already evaluated this course', status=400)

        try:
            CourseEvaluation.objects.create(
                enrollment=enrollment,
                rating=rating,
                comments=comments,
            )
        except IntegrityError:
            return HttpResponse('You have already evaluated this course', status=400)

        return redirect('base-course-evaluation')


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

        rows = []
        if student and session:
            enrollments = list(
                Enrollment.objects
                .filter(
                    student=student,
                    curriculum__session=session,
                    status='approved',
                )
                .select_related('curriculum__course')
                .prefetch_related('curriculum__professor__user')
            )

            if enrollments:
                evaluations = LecturerEvaluation.objects.filter(
                    enrollment__in=enrollments
                )
                evaluation_map = {
                    (ev.enrollment_id, ev.lecturer_id): ev for ev in evaluations
                }

                for enrollment in enrollments:
                    for professor in enrollment.curriculum.professor.all():
                        rows.append({
                            'enrollment': enrollment,
                            'curriculum': enrollment.curriculum,
                            'professor': professor,
                            'evaluation': evaluation_map.get(
                                (enrollment.pk, professor.pk)
                            ),
                        })

        context = {
            'rows': rows,
            'student': student,
            'session': session,
        }
        return render(request, 'base/evaluations/lecturer.html', context)

    def post(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('Invalid request', status=400)

        enrollment_id = request.POST.get('enrollment_id')
        lecturer_id = request.POST.get('lecturer_id')
        rating_raw = request.POST.get('rating')
        comments = request.POST.get('comments', '').strip()

        if not enrollment_id or not lecturer_id or not rating_raw:
            return HttpResponse('Rating is required', status=400)

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            return HttpResponse('Invalid rating', status=400)

        if rating < 1 or rating > 5:
            return HttpResponse('Rating must be between 1 and 5', status=400)

        enrollment = (
            Enrollment.objects
            .filter(
                record_id=enrollment_id,
                student=student,
                curriculum__session=session,
            )
            .first()
        )
        if not enrollment:
            return HttpResponse('Enrollment not found', status=404)

        # Make sure the submitted lecturer is actually assigned to this
        # enrollment's curriculum, not an arbitrary lecturer_id.
        lecturer = enrollment.curriculum.professor.filter(
            record_id=lecturer_id
        ).first()
        if not lecturer:
            return HttpResponse('Lecturer not found for this course', status=404)

        if LecturerEvaluation.objects.filter(
            enrollment=enrollment, lecturer=lecturer
        ).exists():
            return HttpResponse('You have already evaluated this lecturer', status=400)

        try:
            LecturerEvaluation.objects.create(
                enrollment=enrollment,
                lecturer=lecturer,
                rating=rating,
                comments=comments,
            )
        except IntegrityError:
            return HttpResponse('You have already evaluated this lecturer', status=400)

        return redirect('base-lecturer-evaluation')


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

        allocation = (
            HostelAllocation.objects
            .filter(student=student, session=session)
            .select_related('room__hostel')
            .first()
            if student and session else None
        )

        evaluation = None
        category_scores = []
        if allocation:
            evaluation = HostelEvaluation.objects.filter(
                allocation=allocation).first()
            if evaluation:
                category_scores = [
                    (label, getattr(evaluation, f'{key}_rating'))
                    for key, label in HOSTEL_EVALUATION_CATEGORIES
                ]

        context = {
            'allocation': allocation,
            'evaluation': evaluation,
            'student': student,
            'session': session,
            'categories': HOSTEL_EVALUATION_CATEGORIES,
            'category_scores': category_scores,
        }
        return render(request, 'base/evaluations/hostel.html', context)

    def post(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('Invalid request', status=400)

        allocation_id = request.POST.get('allocation_id')
        if not allocation_id:
            return HttpResponse('Invalid request', status=400)

        allocation = HostelAllocation.objects.filter(
            record_id=allocation_id,
            student=student,
            session=session,
        ).first()
        if not allocation:
            return HttpResponse('Allocation not found', status=404)

        if HostelEvaluation.objects.filter(allocation=allocation).exists():
            return HttpResponse('You have already evaluated this allocation', status=400)

        category_ratings = {}
        for key, label in HOSTEL_EVALUATION_CATEGORIES:
            raw = request.POST.get(f'{key}_rating')
            if not raw:
                return HttpResponse(f'{label} rating is required', status=400)
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return HttpResponse(f'Invalid {label} rating', status=400)
            if value < 1 or value > 5:
                return HttpResponse(f'{label} rating must be between 1 and 5', status=400)
            category_ratings[f'{key}_rating'] = value

        overall_raw = request.POST.get('overall_rating')
        if not overall_raw:
            return HttpResponse('Overall rating is required', status=400)
        try:
            overall = int(overall_raw)
        except (TypeError, ValueError):
            return HttpResponse('Invalid overall rating', status=400)
        if overall < 1 or overall > 5:
            return HttpResponse('Overall rating must be between 1 and 5', status=400)

        comments = request.POST.get('comments', '').strip()

        try:
            HostelEvaluation.objects.create(
                allocation=allocation,
                rating=overall,
                comments=comments,
                **category_ratings,
            )
        except IntegrityError:
            return HttpResponse('You have already evaluated this allocation', status=400)

        return redirect('base-hostel-evaluation')
