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


from django.core.exceptions import ValidationError
from decouple import config

from django.http import JsonResponse
from django.shortcuts import (
    render,
)
from django.views import View
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.db import transaction

from base.models import (
    Curriculum,
    Session,
    Enrollment,
    Result,
    Syllabus,
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
        active_session = self.get_active_session()

        syllabus_entries = Syllabus.objects.none()
        years = []
        total_credits = 0

        if student:
            programme = student.class_entered.programme

            # Full programme roadmap — every course a student in this
            # programme will ever take, not just what's been scheduled
            # into a Curriculum slot for their specific class/session.
            # Excludes Retired/Proposed/Under Review — only real,
            # currently-teachable entries should show on the roadmap.
            syllabus_entries = list(
                Syllabus.objects.filter(
                    programme=programme,
                    state__in=Syllabus.SCHEDULABLE_STATES,
                ).select_related('course').order_by('offered', 'course__course_code')
            )

            total_credits = sum(e.course.credits for e in syllabus_entries)

            duration_years = programme.duration_years or 1
            years = list(range(1, duration_years + 1))

            # Attach "currently scheduled" info only for entries actually
            # being taught to THIS student's class in the active session —
            # a future year's units won't have this yet, which is expected.
            if active_session:
                curricula = Curriculum.objects.filter(
                    Tclass=student.class_entered,
                    session=active_session,
                    syllabus__in=syllabus_entries,
                ).select_related('syllabus').prefetch_related('professor__user')

                curriculum_by_syllabus_id = {
                    c.syllabus_id: c for c in curricula
                }

                for entry in syllabus_entries:
                    entry.current_curriculum = curriculum_by_syllabus_id.get(
                        entry.record_id)
            else:
                for entry in syllabus_entries:
                    entry.current_curriculum = None

        context = {
            'syllabus_entries': syllabus_entries,
            'years': years,
            'total_credits': total_credits,
            'student': student,
            'session': active_session,
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
    min_credits = config("MIN_ELECTIVE_CREDITS", default=2, cast=int)
    max_credits = config("MAX_ELECTIVE_CREDITS", default=21, cast=int)

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled = []
        active_curriculum_ids = []
        available = Curriculum.objects.none()

        if student and session:
            enrolled_qs = Enrollment.objects.filter(
                student=student,
                curriculum__session=session,
            ).exclude(
                status='dropped'
            ).select_related(
                'curriculum__syllabus__course'
            ).order_by('curriculum__syllabus__course__course_code')

            active_curriculum_ids = list(
                enrolled_qs.values_list('curriculum_id', flat=True)
            )

            enrolled = list(enrolled_qs)

            # Published results for every enrolled row, fetched in one
            # query rather than N+1 through the `.results` property.
            enrollment_ids = [e.record_id for e in enrolled]
            published_results = Result.objects.filter(
                enrollment_id__in=enrollment_ids,
                state='published',
            ).order_by('type')

            results_map = {}
            for r in published_results:
                results_map.setdefault(str(r.enrollment_id), []).append({
                    'type': r.get_type_display(),
                    'title': r.title,
                    'score': float(r.score),
                })

            for e in enrolled:
                e.published_results_list = results_map.get(
                    str(e.record_id), [])

            available = Curriculum.objects.filter(
                Tclass=student.class_entered,
                session=session,
                syllabus__course__course_type='E',
            ).exclude(
                record_id__in=active_curriculum_ids
            ).select_related('syllabus__course')

        context = {
            'available': available,
            'enrolled': enrolled,
            'results_by_enrollment': results_map,
            'student': student,
            'session': session,
            'min_credits': self.min_credits,
            'max_credits': self.max_credits,
        }
        return render(request, 'base/academics/unit_registration.html', context)

    def post(self, request):
        """
        Enroll in one or more selected elective units, pending department
        approval. Uses get_or_create + manual reset on the Enrollment
        model directly rather than the M2M `.add()` convenience — a
        previously DROPPED unit already has an Enrollment row for
        (student, curriculum), and unique_together on that pair means a
        second insert isn't possible. Re-registering has to reset the
        existing row instead of creating a new one.
        """
        student = self.get_student(request)
        session = self.get_active_session()
        curriculum_ids = request.POST.getlist('curriculum_ids')

        if not student or not session or not curriculum_ids:
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        active_curriculum_ids = Enrollment.objects.filter(
            student=student,
            curriculum__session=session,
        ).exclude(status='dropped').values_list('curriculum_id', flat=True)

        curricula = Curriculum.objects.filter(
            record_id__in=curriculum_ids,
            Tclass=student.class_entered,
            session=session,
            syllabus__course__course_type='E',
        ).exclude(
            record_id__in=active_curriculum_ids
        ).select_related('syllabus__course')

        if not curricula.exists():
            return JsonResponse({'success': False, 'message': 'No matching units found.'}, status=404)

        total_credits = sum(c.course.credits for c in curricula)

        if total_credits < self.min_credits:
            return JsonResponse({
                'success': False,
                'message': f"Minimum {self.min_credits} credits required — you selected {total_credits}.",
            }, status=400)

        if total_credits > self.max_credits:
            return JsonResponse({
                'success': False,
                'message': f"Maximum {self.max_credits} credits allowed — you selected {total_credits}.",
            }, status=400)

        with transaction.atomic():
            for curriculum in curricula:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    curriculum=curriculum,
                    defaults={'status': 'pending', 'approval_method': None},
                )
                if not created and enrollment.status == 'dropped':
                    enrollment.status = 'pending'
                    enrollment.approval_method = None
                    enrollment.approved_by = None
                    enrollment.approved_at = None
                    enrollment.save()

        return JsonResponse({
            'success': True,
            'message': f"{curricula.count()} unit(s) submitted for approval.",
        })


class DropElectiveUnitView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """Student self-service drop — electives only, pre-grading only."""

    def post(self, request):
        student = self.get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'No student profile.'}, status=403)

        enrollment_id = request.POST.get('enrollment_id')
        enrollment = Enrollment.objects.filter(
            record_id=enrollment_id,
            student=student,
        ).select_related('curriculum__syllabus__course').first()

        if not enrollment:
            return JsonResponse({'success': False, 'message': 'Enrollment not found.'}, status=404)

        if enrollment.curriculum.course.course_type != 'E':
            return JsonResponse({
                'success': False,
                'message': 'Only elective units can be dropped here.',
            }, status=400)

        if enrollment.status == 'dropped':
            return JsonResponse({'success': False, 'message': 'This unit is already dropped.'}, status=400)

        try:
            enrollment.drop()
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': ' '.join(e.messages)}, status=400)

        return JsonResponse({
            'success': True,
            'message': f"{enrollment.curriculum.course.course_code} dropped.",
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
                curricula__Tclass=target_class
            ).order_by('start_date').first()

            if not earliest_session:
                sessions = Session.objects.none()  # Return empty if class has no history
            else:
                # 2. Grab every session from that start date up until the current timeline
                sessions = Session.objects.filter(
                    start_date__gte=earliest_session.start_date
                ).order_by('start_date')
                results = Result.objects.filter(
                    enrollment__student=student
                ).select_related('enrollment__curriculum__syllabus__course').order_by('-created_at')

        context = {
            'results': results,
            'student': student,
            'session': session,
            'sessions': sessions
        }
        return render(request, 'base/academics/results.html', context)
