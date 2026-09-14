from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from base.models import (
    Curriculum,
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
            # `professor` is still an M2M (through LecturerAssignment),
            # so filtering by it directly still works fine.
            .filter(
                professor=lecturer,
                session=session
            )
            # syllabus__course -> course (direct FK again); Tclass no
            # longer exists as a direct field — see NOTE below on
            # `classes` (M2M) replacing it, and the template implication.
            .select_related('course')
            .prefetch_related('professor', 'classes')
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
        # counts one row per (course, session) curriculum entry.
        #
        # NOTE: Curriculum.unique_together is now (course, session), so
        # under the new schema every row returned by this filter is
        # already a distinct course by construction — this could be
        # simplified to units.count() (or a plain .count() on the same
        # filter). Kept as an explicit values('course').distinct().count()
        # for clarity and to stay resilient if unique_together ever
        # loosens, but it's redundant right now, unlike under the old
        # schema where one course could legitimately have several
        # Curriculum rows (one per class) and this dedup was load-bearing.
        distinct_course_count = (
            Curriculum.objects
            .filter(
                professor=lecturer,
                session=session
            )
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

        # `curriculum__Tclass` no longer exists on Timetable's join path.
        # A Timetable slot points at a Curriculum that can now serve
        # several classes at once, so there's no single Tclass to
        # select_related through it here. `curriculum__classes` is
        # prefetched instead — the template needs to iterate
        # `slot.curriculum.classes.all()` (or similar) to list which
        # class(es) a given lecture slot serves, rather than reading a
        # single `slot.curriculum.Tclass`. Flagging this explicitly since
        # it's a template-level change, not just a queryset rename.
        today_slots = (
            Timetable.objects
            .filter(
                curriculum__professor=lecturer,
                curriculum__session=session,
                day=today_code,
            )
            .select_related('curriculum__course', 'venue')
            .prefetch_related('curriculum__classes')
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
            .order_by(
                'exam_venue__exam_session__date', 'exam_venue__exam_session__time_slot'
            )
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
