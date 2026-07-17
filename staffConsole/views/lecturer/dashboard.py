from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from base.models import (
    Curriculum,
    ExamVenue,
    Session,
    Timetable,
    ExamInvigilatorAssignment
)
from staffConsole.views.base import RoleRequiredMixin
from django.views import View


class LecturerDashboardView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/dashboard.html'

    _DAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI'}

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()
        today_code = self._DAY_MAP.get(timezone.now().weekday())

        units = (
            Curriculum.objects
            # check if this works for through tables
            .filter(professor=lecturer, session=session)
            .select_related('course', 'Tclass')
            .prefetch_related('professor')
            .annotate(
                approved_count=Count(
                    'enrollment_records',
                    filter=Q(enrollment_records__status='approved'),
                    distinct=True,
                ),
                entered_count=Count(
                    'enrollment_records__student',
                    filter=Q(
                        enrollment_records__status='approved',
                        enrollment_records__results__record_id__isnull=False,
                    ),
                    distinct=True,
                ),
            )
            .distinct()
            if session else []
        )

        # Distinct *courses* taught this session — dedupes across classes/
        # programmes that share the same course, unlike len(units) which
        # counts one row per (course, class, session) curriculum entry.
        distinct_course_count = (
            Curriculum.objects
            .filter(professor=lecturer, session=session)
            .values('course')
            .distinct()
            .count()
            if session else 0
        )

        results_progress = [
            {
                'unit':    unit,
                'total':   unit.approved_count,
                'entered': unit.entered_count,
                'pct':     (
                    round(unit.entered_count / unit.approved_count * 100)
                    if unit.approved_count else 0
                ),
            }
            for unit in units
        ]

        today_slots = (
            Timetable.objects
            .filter(
                curriculum__professor=lecturer,
                curriculum__session=session,
                day=today_code,
            )
            .select_related('curriculum__course', 'curriculum__Tclass', 'venue')
            .order_by('time_slot')
            if (session and today_code) else []
        )

        invigilation = (
            ExamInvigilatorAssignment.objects
            .filter(
                lecturer=lecturer,
                exam_venue__exam_session__curriculum__session=session,
            )
            .select_related(
                'exam_venue__exam_session__curriculum__course',
                'exam_venue__exam_session',
                'exam_venue__venue',
            )
            .order_by('exam_venue__exam_session__date', 'exam_venue__exam_session__time_slot')
            if session else []
        )

        pending_results = [r for r in results_progress if r['pct'] < 100]
        total_students = sum(r['total'] for r in results_progress)

        return render(request, self.template_name, {
            **self.get_context_data(),
            'session':               session,
            'units':                 units,
            'distinct_course_count': distinct_course_count,
            'results_progress':      results_progress,
            'today_slots':           today_slots,
            'today_date':            timezone.now().date(),
            'invigilation':          invigilation,
            'pending_results':       pending_results,
            'total_students':        total_students,
        })
