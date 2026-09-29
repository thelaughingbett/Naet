# transcript_utils.py
"""
Buckets a student's sessions into "years of study" — Year 1, Year 2, etc.
— purely by calendar position (programme.semesters_per_year sessions per
bucket), independent of grades or retakes, and skipping any session the
student was deferred for. Both the year picker (ResultsView) and the
PDF endpoint (transcript_pdf) import this, so they can never disagree
about which sessions belong to which year.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set

from base.models import Session


@dataclass
class StudyYear:
    year: int
    sessions: List[Session] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"Year {self.year}"

    @property
    def academic_year_label(self) -> str:
        years = sorted(
            {s.academic_year for s in self.sessions if s.academic_year})
        return " / ".join(years) if years else ""

    @property
    def has_data(self) -> bool:
        return len(self.sessions) > 0


def _deferred_session_ids(student) -> Set:
    """
    Session record_ids to exclude from year bucketing.

    A deferment spans from session_deferred (inclusive — the student
    didn't attend that session) up to but not including
    session_returning (the student resumes there, which counts normally).
    An approved deferment with no session_returning set yet excludes
    every session from session_deferred onward, since it's still open.

    Withdrawn deferment requests never took effect, so a session is
    only excluded for deferments whose request was actually approved —
    a merely 'requested'/pending or 'rejected' deferment never skipped
    anything.
    """
    from base.models import Deferment

    excluded: Set = set()

    deferments = Deferment.objects.filter(
        student=student,
        request_status='approved',
    ).select_related('session_deferred', 'session_returning')

    for d in deferments:
        start = d.session_deferred.start_date
        if d.session_returning_id:
            end = d.session_returning.start_date
            qs = Session.objects.filter(
                start_date__gte=start, start_date__lt=end)
        else:
            qs = Session.objects.filter(start_date__gte=start)
        excluded.update(qs.values_list('record_id', flat=True))

    return excluded


def get_study_years(student) -> List[StudyYear]:
    programme = student.class_entered.programme
    semesters_per_year = programme.semesters_per_year or 2

    earliest_session = Session.objects.filter(
        curricula__classes=student.class_entered
    ).order_by('start_date').first()

    if not earliest_session:
        return []

    deferred_ids = _deferred_session_ids(student)

    all_sessions = [
        s for s in Session.objects.filter(
            start_date__gte=earliest_session.start_date
        ).order_by('start_date')
        if s.record_id not in deferred_ids
    ]

    years = []
    for i in range(0, len(all_sessions), semesters_per_year):
        chunk = all_sessions[i:i + semesters_per_year]
        years.append(
            StudyYear(year=(i // semesters_per_year) + 1, sessions=chunk))
    return years


def get_study_year(student, year: int) -> Optional[StudyYear]:
    return next((sy for sy in get_study_years(student) if sy.year == year), None)
