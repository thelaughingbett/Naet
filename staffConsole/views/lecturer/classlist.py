# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import csv
import math
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import (
    Curriculum,
    Enrollment,
    Result,
    Session,
    Timetable,
)
from base.modules.academics.grading_service import GradingService, PREVIEW
from staffConsole.views.base import RoleRequiredMixin


PAGE_SIZE = 10          # never more than ten students per page

VALID_STATUS = ('approved', 'pending', 'rejected')
VALID_RESULTS = ('entered', 'not_entered')
NO_GRADE = '—'

# table-header key -> row field
SORT_FIELDS = {
    'name':   'full_name',
    'reg':    'registration_no',
    'class':  'class_name',
    'email':  'school_email',
    'status': 'status',
    'total':  'total',
    'grade':  'grade',
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers - NOTHING here computes a score or a grade; GradingService does.
# ─────────────────────────────────────────────────────────────────────────────

def _build_student_row(enrollment, outcome, has_results) -> dict:
    """
    One display row. `outcome` is the GradingService answer for this
    enrollment (lecturer view = PREVIEW, so it matches Enter Results exactly).
    total/grade stay None / '—' until the weighted final is complete.

    `class_name` is THIS student's own Tclass, not the (possibly shared,
    multi-class) curriculum.classes set.
    """
    student = enrollment.student
    user = student.user

    return {
        'enrollment_id':   str(enrollment.record_id),
        'student_id':      str(student.record_id),
        'registration_no': student.registration_number,
        'full_name':       user.full_name,
        'initials':        user.initials,
        'email':           user.email,
        'school_email':    student.school_email or '',
        'class_name':      (
            student.class_entered.class_name if student.class_entered else '—'
        ),
        'status':          enrollment.status,       # pending | approved | rejected
        'total':           outcome.score,           # Decimal | None
        'grade':           outcome.grade_letter or NO_GRADE,
        'outcome':         outcome.status,          # pass | fail | in_progress
        'results_entered': has_results,             # any result recorded at all
        'attendance':      None,   # placeholder - no Attendance model yet
    }


def _load_rows(curriculum):
    """
    Every enrollment of the curriculum as display rows, plus the grade letters
    of the active scale (for the filter dropdown). Two queries for the grading
    data in total; class sizes are hundreds, so filter/sort/page run in memory.
    """
    svc = GradingService()
    enrollments = list(
        Enrollment.objects
        .filter(curriculum=curriculum)
        .select_related('student__user', 'student__class_entered',
                        'curriculum__course')
        .order_by('student__registration_number')
    )
    by_enr = svc.fetch_results([e.record_id for e in enrollments], PREVIEW)

    rows = []
    for e in enrollments:
        results = by_enr.get(str(e.record_id), [])
        outcome = svc.outcome(e, results=results, states=PREVIEW)
        rows.append(_build_student_row(e, outcome, bool(results)))

    return rows, svc.policy_for(curriculum).grade_labels


def _stats(rows):
    return {
        'total':    len(rows),
        'approved': sum(1 for r in rows if r['status'] == 'approved'),
        'pending':  sum(1 for r in rows if r['status'] == 'pending'),
        'rejected': sum(1 for r in rows if r['status'] == 'rejected'),
    }


def _params(get):
    """Parse + whitelist the list query-string (works for QueryDict or dict)."""
    def pick(name, valid):
        v = get.get(name, '')
        return v if v in valid else ''

    return {
        'q':       (get.get('q') or '').strip(),
        'klass':   get.get('class', ''),
        'status':  pick('status', VALID_STATUS),
        'grade':   get.get('grade', ''),          # compared by equality only
        'results': pick('results', VALID_RESULTS),
        'sort':    pick('sort', SORT_FIELDS),
        'dir':     'desc' if get.get('dir') == 'desc' else 'asc',
        'page':    get.get('page', 1),
    }


def _filter_rows(rows, p):
    q = p['q'].lower()

    def ok(r):
        if q and not (q in r['full_name'].lower()
                      or q in r['registration_no'].lower()
                      or q in r['school_email'].lower()):
            return False
        if p['klass'] and r['class_name'] != p['klass']:
            return False
        if p['status'] and r['status'] != p['status']:
            return False
        if p['grade'] and r['grade'] != p['grade']:
            return False
        if p['results'] == 'entered' and not r['results_entered']:
            return False
        if p['results'] == 'not_entered' and r['results_entered']:
            return False
        return True

    return [r for r in rows if ok(r)]


def _sort_rows(rows, p):
    field = SORT_FIELDS.get(p['sort'])
    if not field:
        return rows                      # already ordered by registration no.

    def blank(v):
        return v is None or v == '' or v == NO_GRADE

    missing = [r for r in rows if blank(r[field])]
    present = [r for r in rows if not blank(r[field])]
    present.sort(
        key=lambda r: r[field] if field == 'total' else str(r[field]).lower(),
        reverse=p['dir'] == 'desc',
    )
    return present + missing             # blanks always last


def _paginate(rows, page):
    total = len(rows)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page = min(max(page, 1), pages)

    start = (page - 1) * PAGE_SIZE
    chunk = rows[start:start + PAGE_SIZE]
    return chunk, {
        'page':      page,
        'pages':     pages,
        'total':     total,
        'page_size': PAGE_SIZE,
        'start':     start + 1 if total else 0,
        'end':       start + len(chunk),
    }


def _row_json(r):
    """Row -> JSON-safe dict (Decimals become strings, None stays null)."""
    return {
        'enrollment_id':   r['enrollment_id'],
        'registration_no': r['registration_no'],
        'full_name':       r['full_name'],
        'initials':        r['initials'],
        'school_email':    r['school_email'],
        'class_name':      r['class_name'],
        'status':          r['status'],
        'total':           None if r['total'] is None else str(r['total']),
        'grade':           r['grade'],
        'outcome':         r['outcome'],
    }


def _payload(all_rows, grade_labels, p):
    """One page of rows, filtered and sorted over ALL of the class."""
    filtered = _sort_rows(_filter_rows(all_rows, p), p)
    chunk, pagination = _paginate(filtered, p['page'])
    return {
        'rows':          [_row_json(r) for r in chunk],
        'pagination':    pagination,
        'classes':       sorted({r['class_name'] for r in all_rows}),
        'grade_options': grade_labels,
    }


def _get_curriculum(lecturer, curriculum_id):
    try:
        return (Curriculum.objects.select_related('course')
                .get(record_id=curriculum_id, professor=lecturer))
    except (Curriculum.DoesNotExist, ValueError, ValidationError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────

class ClassListView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/class_list.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        all_units = (
            Curriculum.objects
            .filter(professor=lecturer, session=session)
            .select_related('course', 'session')
            .prefetch_related('classes')
            .order_by('course__course_code')
            if session else []
        )

        selected_id = request.GET.get('curriculum')
        selected = None
        if all_units:
            if selected_id:
                selected = next(
                    (u for u in all_units if str(u.record_id) == selected_id),
                    None
                )
            selected = selected or all_units[0]

        # ── course selector list (lightweight - no student data) ──────────
        unit_list = []
        for unit in all_units:
            slot = (
                Timetable.objects
                .filter(curriculum=unit)
                .select_related('venue')
                .order_by('day', 'time_slot')
                .first()
            )
            unit_list.append({
                'curriculum':     unit,
                'slot':           slot,
                'total_enrolled': unit.enrollment_records.filter(
                    status='approved'
                ).count(),
            })

        # ── first page of the selected curriculum ─────────────────────────
        stats = {}
        selected_slot = None
        initial_payload = {
            'rows': [],
            'pagination': {'page': 1, 'pages': 1, 'total': 0,
                           'page_size': PAGE_SIZE, 'start': 0, 'end': 0},
            'classes': [],
            'grade_options': [],
        }

        if selected:
            all_rows, labels = _load_rows(selected)
            stats = _stats(all_rows)
            initial_payload = _payload(all_rows, labels, _params({}))
            selected_slot = (
                Timetable.objects
                .filter(curriculum=selected)
                .select_related('venue')
                .order_by('day', 'time_slot')
                .first()
            )

        context = {
            **self.get_context_data(),
            'session':         session,
            'unit_list':       unit_list,
            'selected':        selected,
            'selected_slot':   selected_slot,
            'initial_payload': initial_payload,     # rendered with |json_script
            'stats':           stats,
            'lecturer':        lecturer,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX - one page of students (search / filters / sort / page)
# ─────────────────────────────────────────────────────────────────────────────

class ClassListDataAjaxView(RoleRequiredMixin, View):
    """
    GET ?curriculum=<uuid>&page=<n>&q=&class=&status=&grade=&results=
        &sort=<name|reg|class|email|status|total|grade>&dir=<asc|desc>
    """
    required_role = 'lecturer'

    def get(self, request):
        curriculum = _get_curriculum(
            self.get_profile(), request.GET.get('curriculum'))
        if curriculum is None:
            return JsonResponse({'error': 'Not found'}, status=404)

        rows, labels = _load_rows(curriculum)
        return JsonResponse(_payload(rows, labels, _params(request.GET)))


# ─────────────────────────────────────────────────────────────────────────────
# AJAX - every recipient matching the current filters (for "Email All")
# ─────────────────────────────────────────────────────────────────────────────

class ClassListRecipientsAjaxView(RoleRequiredMixin, View):
    """Same filter params as above (page/sort ignored)."""
    required_role = 'lecturer'

    def get(self, request):
        curriculum = _get_curriculum(
            self.get_profile(), request.GET.get('curriculum'))
        if curriculum is None:
            return JsonResponse({'error': 'Not found'}, status=404)

        rows, _ = _load_rows(curriculum)
        rows = _filter_rows(rows, _params(request.GET))
        recipients = [
            {'email': r['school_email'], 'name': r['full_name']}
            for r in rows if r['school_email']
        ]
        return JsonResponse({'recipients': recipients, 'matched': len(rows)})


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV - every row matching the current filters/sort, not just one page
# ─────────────────────────────────────────────────────────────────────────────

def _csv_safe(v):
    """Neutralise spreadsheet formula injection (=, +, -, @ at cell start)."""
    s = '' if v is None else str(v)
    return "'" + s if s[:1] in ('=', '+', '-', '@') else s


class ClassListExportView(RoleRequiredMixin, View):
    """GET /lecturer/class-list/export/?curriculum=...&<filters>"""
    required_role = 'lecturer'

    def get(self, request):
        curriculum = _get_curriculum(
            self.get_profile(), request.GET.get('curriculum'))
        if curriculum is None:
            return HttpResponse('Not found', status=404)

        p = _params(request.GET)
        rows, _ = _load_rows(curriculum)
        rows = _sort_rows(_filter_rows(rows, p), p)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        code = curriculum.course.course_code
        response['Content-Disposition'] = (
            f'attachment; filename="{code}_classlist.csv"')
        response.write('\ufeff')            # BOM so Excel reads UTF-8
        w = csv.writer(response)
        w.writerow(['#', 'Name', 'Reg No', 'Class', 'Email',
                    'Status', 'Total', 'Grade'])
        for i, r in enumerate(rows, 1):
            w.writerow([
                i,
                _csv_safe(r['full_name']),
                _csv_safe(r['registration_no']),
                _csv_safe(r['class_name']),
                _csv_safe(r['school_email']),
                r['status'].title(),
                '' if r['total'] is None else r['total'],
                '' if r['grade'] == NO_GRADE else r['grade'],
            ])
        return response


# ─────────────────────────────────────────────────────────────────────────────
# AJAX - student detail (for view modal)
# ─────────────────────────────────────────────────────────────────────────────

class StudentDetailAjaxView(RoleRequiredMixin, View):
    """
    GET /lecturer/class-list/student/<enrollment_id>/
    Same GradingService outcome as the table row and the Enter Results page,
    plus the per-component breakdown that produced it.
    """
    required_role = 'lecturer'

    def get(self, request, enrollment_id):
        try:
            enrollment = (
                Enrollment.objects
                .select_related(
                    'student__user',
                    'student__class_entered',
                    'curriculum__course',
                )
                .get(record_id=enrollment_id)
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        lecturer = self.get_profile()
        if not enrollment.curriculum.professor.filter(pk=lecturer.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        student = enrollment.student
        user = student.user

        svc = GradingService()
        results = list(
            Result.objects
            .filter(enrollment=enrollment)
            .order_by('type', 'title')
        )
        outcome = svc.outcome(enrollment, results=results, states=PREVIEW)
        policy = svc.policy_of(enrollment)

        breakdown = []
        for c in policy.components:
            s = outcome.components.get(c.result_type)
            breakdown.append({
                'label':  c.get_result_type_display(),
                'weight': format(c.weight_percent.normalize(), 'f'),
                'score':  None if s is None else str(s),
            })

        return JsonResponse({
            'enrollment_id':   str(enrollment.record_id),
            'student_id':      str(student.record_id),
            'registration_no': student.registration_number,
            'full_name':       user.full_name,
            'email':           user.email,
            'school_email':    student.school_email,
            'class_name':      (
                student.class_entered.class_name if student.class_entered else '—'
            ),
            'status':          enrollment.status,
            'total':           None if outcome.score is None else str(outcome.score),
            'grade':           outcome.grade_letter or NO_GRADE,
            'outcome':         outcome.status,
            'frozen':          outcome.frozen,
            'breakdown':       breakdown,
            'results': [
                {'type': r.get_type_display(), 'title': r.title,
                 'score': str(r.score), 'state': r.state}
                for r in results
            ],
            'course_code':     enrollment.curriculum.course.course_code,
            'course_name':     enrollment.curriculum.course.course_name,
        })
