# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from django.views import View

from base.models import (
    Curriculum,
    Result,
    Session,
    Timetable,
    ExamInvigilatorAssignment
)
from staffConsole.views.base import RoleRequiredMixin


class MyCourseView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/my_courses.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        # ── curriculum entries assigned to this lecturer this session ─────
        units = (
            Curriculum.objects
            .filter(professor=lecturer, session=session)
            .select_related('syllabus__course', 'Tclass', 'session')
            .prefetch_related('professor')
            if session else []
        )

        distinct_course_count = (
            Curriculum.objects
            .filter(professor=lecturer, session=session)
            .values('syllabus__course')
            .distinct()
            .count()
            if session else 0
        )
        # ── per-unit statistics ───────────────────────────────────────────
        # approved_enrollments  — denominator for results %
        # results_entered       — students who have at least one Result row
        #                         for this curriculum entry
        course_rows = []
        for unit in units:
            approved = unit.enrollment_records.filter(
                status='approved').count()
            entered = (
                Result.objects
                .filter(enrollment__curriculum=unit)
                .values('enrollment__student')
                .distinct()
                .count()
            )
            pct = round(entered / approved * 100) if approved else 0

            # first timetable slot for display (day + time)
            slot = (
                Timetable.objects
                .filter(curriculum=unit)
                .select_related('venue')
                .order_by('day', 'time_slot')
                .first()
            )

            course_rows.append({
                'curriculum':  unit,
                'approved':    approved,
                'entered':     entered,
                'pct':         pct,
                'slot':        slot,      # may be None if not yet timetabled
            })

        # ── aggregate stats for the stat cards ───────────────────────────
        total_students = sum(r['approved'] for r in course_rows)
        results_pending = [r for r in course_rows if r['pct'] < 100]
        invigilation_duties = (
            ExamInvigilatorAssignment.objects
            .filter(
                lecturer=lecturer,
                exam_venue__exam_session__curriculum__session=session,
            )
            .select_related(
                'exam_venue__exam_session__curriculum__syllabus__course',
                'exam_venue__exam_session',
                'exam_venue__venue',
            )
            .order_by('exam_venue__exam_session__date', 'exam_venue__exam_session__time_slot')
            if session else []
        )

        # ── unique sessions across these units (for the semester filter) ──
        # We include the active session plus any past sessions the lecturer
        # also has curriculum entries for (e.g. they were kept on from prev)
        all_lecturer_sessions = (
            Session.objects
            .filter(curricula__professor=lecturer)
            .distinct()
            .order_by('-academic_year', '-semester')
            if lecturer else []
        )

        context = {
            **self.get_context_data(),
            'distinct_course_count': distinct_course_count,
            'session':             session,
            'course_rows':         course_rows,
            'total_students':      total_students,
            'results_pending':     results_pending,
            'invigilation_duties': list(invigilation_duties),
            'all_sessions':        all_lecturer_sessions,
        }
        return render(request, self.template_name, context)
