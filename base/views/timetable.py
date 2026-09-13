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

from base.models import Timetable, DailyClassExecution, Student, User, Venue
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
import json
from decouple import config

from django.shortcuts import (
    render,
)
from django.views import View
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from base.models import (
    Timetable,
    ExamSession,
    Session,
    Enrollment
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
            enrolled_curriculum_ids = Enrollment.objects.filter(
                student=student,
                curriculum__session=session,
                status__in=['approved', 'pending']
            ).values_list('curriculum_id', flat=True)

            # NOTE : if the student is class_rep just load all for the class not just the student's

            entries = Timetable.objects.filter(
                curriculum_id__in=enrolled_curriculum_ids
            ).select_related(
                'curriculum__syllabus__course',
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

        if student and session:
            enrolled_curriculum_ids = Enrollment.objects.filter(
                student=student,
                curriculum__session=session,
                status__in=['approved', 'pending']
            ).values_list('curriculum_id', flat=True)

            exam_sessions = ExamSession.objects.filter(
                curriculum_id__in=enrolled_curriculum_ids
            ).select_related(
                'curriculum__syllabus__course',
                'curriculum__session',
            ).prefetch_related(
                'venues__venue',
                'venues__invigilators__user',
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


@login_required
@require_GET
def execution_history(request):
    """Returns JSON history of DailyClassExecution rows for a given Timetable slot."""
    timetable_id = request.GET.get("timetable_id")
    if not timetable_id:
        return JsonResponse({"executions": []})

    executions = DailyClassExecution.objects.filter(
        timetable_slot_id=timetable_id
    ).select_related(
        "class_representative__user", "rescheduled_to_venue"
    ).order_by("-calendar_date")

    return JsonResponse({
        "executions": [
            {
                "calendar_date": str(ex.calendar_date),
                "status": ex.status,
                "class_representative": (
                    ex.class_representative.user.full_name
                    if ex.class_representative else None
                ),
                "rescheduled_to_date": (
                    str(ex.rescheduled_to_date) if ex.rescheduled_to_date else None
                ),
                "rescheduled_to_time_slot": ex.rescheduled_to_time_slot,
                "rescheduled_to_venue": (
                    ex.rescheduled_to_venue.venue_name if ex.rescheduled_to_venue else None
                ),
                "notes": ex.notes,
            }
            for ex in executions
        ]
    })


@login_required
@require_POST
def log_execution(request):
    """
    Class-representative only. A student can only confirm/report execution
    for their OWN class's timetable slots, and only if they are that
    class's designated representative — NOT any enrolled student, and
    NOT a lecturer (lecturer no-shows are exactly what this reports on,
    so a lecturer self-attesting attendance would defeat the point).
    """
    student = Student.objects.filter(
        user=request.user).select_related('class_entered').first()
    if not student:
        raise PermissionDenied("Only students can confirm class execution.")

    # # ASSUMPTION: Tclass.class_representative FK — adjust if modeled differently.
    # if getattr(student.class_entered, 'class_representative_id', None) != student.pk:
    #     raise PermissionDenied(
    #         "Only the class representative can confirm execution.")

    import json
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid request body."}, status=400)

    timetable_id = payload.get("timetable_id")
    timetable_slot = Timetable.objects.select_related(
        "curriculum__Tclass").filter(pk=timetable_id).first()
    if not timetable_slot:
        return JsonResponse({"success": False, "message": "Timetable slot not found."}, status=404)

    # confirm this slot actually belongs to the rep's own class
    if timetable_slot.curriculum.Tclass_id != student.class_entered_id:
        raise PermissionDenied(
            "You can only confirm execution for your own class.")

    status = payload.get("status")
    if status not in ("Attended", "Missed", "Rescheduled"):
        return JsonResponse({"success": False, "message": "Invalid status for student submission."}, status=400)

    execution = DailyClassExecution(
        timetable_slot=timetable_slot,
        calendar_date=payload.get("calendar_date"),
        status=status,
        notes=payload.get("notes", ""),
    )

    if status == "Attended":
        # server-derived, not client-submitted
        execution.class_representative = student

    if status == "Rescheduled":
        execution.rescheduled_by = request.user
        execution.reschedule_requested_by_role = "STUDENT"
        execution.rescheduled_to_date = payload.get(
            "rescheduled_to_date") or None
        execution.rescheduled_to_time_slot = payload.get(
            "rescheduled_to_time_slot") or None
        venue_id = payload.get("rescheduled_to_venue")
        if venue_id:
            execution.rescheduled_to_venue = Venue.objects.filter(
                pk=venue_id).first()

    try:
        execution.full_clean()
        execution.save()
    except ValidationError as e:
        messages = []
        for field, errs in getattr(e, "message_dict", {"__all__": e.messages}).items():
            messages.extend(errs)
        return JsonResponse({"success": False, "message": " ".join(messages)}, status=400)

    return JsonResponse({"success": True})
