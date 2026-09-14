# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import json

from django.shortcuts import render
from django.utils import timezone
from django.views import View

from base.models import ExamInvigilatorAssignment, Session
from staffConsole.views.base import RoleRequiredMixin


def _derive_status(exam_session):
    """
    Derived from date + time_slot — neither ExamSession nor ExamVenue has a
    status field. There's also no 'cancelled' state in the schema at all;
    if that's needed, it belongs as a real field on ExamSession rather than
    something inferred here.
    """
    now = timezone.localtime()
    today = now.date()

    if exam_session.date > today:
        return 'upcoming'
    if exam_session.date < today:
        return 'completed'

    # same day — compare against the slot's start/end times
    try:
        start_h, start_m = (int(x) for x in exam_session.slot_start.split(':'))
        end_h, end_m = (int(x) for x in exam_session.slot_end.split(':'))
        start_dt = now.replace(
            hour=start_h, minute=start_m, second=0, microsecond=0)
        end_dt = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return 'upcoming'

    if now < start_dt:
        return 'upcoming'
    if now > end_dt:
        return 'completed'
    return 'ongoing'


def _serialize(duty: ExamInvigilatorAssignment) -> dict:
    exam_session = duty.exam_venue.exam_session
    curriculum = exam_session.curriculum
    course = curriculum.course

    approved_count = curriculum.enrollment_records.filter(
        status='approved').count()

    # A shared Curriculum slot can now serve multiple classes at once
    # (e.g. two programmes sitting the same exam together) — join them
    # rather than assuming exactly one, same as the class-list fix.
    class_names = ", ".join(
        curriculum.classes.values_list('class_name', flat=True)
    )

    return {
        'id':            str(duty.record_id),
        'date':          exam_session.date.isoformat(),
        'time':          exam_session.time_slot.replace('-', ' – '),
        'course_code':   course.course_code,
        'course_title':  course.course_name,
        'class_name':    class_names,
        'venue':         duty.exam_venue.venue.venue_name,
        'type':          exam_session.exam_type,
        'type_display':  exam_session.get_exam_type_display(),
        'status':        _derive_status(exam_session),
        'students':      approved_count,
        # TODO: no field for this anywhere (ExamSession, ExamVenue,
        # Curriculum) — add one if per-duty instructions need to be real.
        'instructions':  None,
    }


class InvigilationDutiesView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/invigilation_duties.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        duties_qs = (
            ExamInvigilatorAssignment.objects
            .filter(
                lecturer=lecturer,
                exam_venue__exam_session__curriculum__session=session,
            )
            .select_related(
                'exam_venue__exam_session__curriculum__course',
                'exam_venue__venue',
            )
            .prefetch_related(
                'exam_venue__exam_session__curriculum__classes',
            )
            .order_by('exam_venue__exam_session__date', 'exam_venue__exam_session__time_slot')
            if session else ExamInvigilatorAssignment.objects.none()
        )

        duties = [_serialize(d) for d in duties_qs]

        total = len(duties)
        upcoming = sum(1 for d in duties if d['status'] in (
            'upcoming', 'ongoing'))
        completed = sum(1 for d in duties if d['status'] == 'completed')
        venue_count = len({d['venue'] for d in duties})

        context = {
            **self.get_context_data(),
            'session':        session,
            'lecturer':       lecturer,
            'duties_json':    json.dumps(duties),
            'stat_total':     total,
            'stat_upcoming':  upcoming,
            'stat_completed': completed,
            'stat_venues':    venue_count,
        }
        return render(request, self.template_name, context)
