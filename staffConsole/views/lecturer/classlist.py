# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from decimal import Decimal

from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import (
    Curriculum,
    Enrollment,
    Result,
    Session,
    Timetable,
)
from staffConsole.views.base import RoleRequiredMixin


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _grade_from_total(total: Decimal) -> str:
    """Map a raw score total to a letter grade."""
    if total >= 70:
        return 'A'
    if total >= 60:
        return 'B'
    if total >= 50:
        return 'C'
    if total >= 40:
        return 'D'
    return 'F'


def _build_student_row(enrollment: Enrollment, results_by_student: dict) -> dict:
    """
    Build a display dict for one enrolled student.

    results_by_student = {student_id: {'cat': Decimal, 'exam': Decimal}}
    No Attendance model yet — attendance field is None until implemented.
    """
    student = enrollment.student
    user = student.user
    scores = results_by_student.get(str(student.record_id), {})
    cat = scores.get('cat',  Decimal('0'))
    exam = scores.get('exam', Decimal('0'))
    total = cat + exam

    return {
        'enrollment_id':     str(enrollment.record_id),
        'student_id':        str(student.record_id),
        'registration_no':   student.registration_number,
        'full_name':         user.full_name,
        'initials':          user.initials,
        'email':             user.email,
        'school_email':      student.school_email,
        'status':            enrollment.status,          # pending | approved | rejected
        'cat':               cat,
        'exam':              exam,
        'total':             total,
        'grade':             _grade_from_total(total) if (cat or exam) else '—',
        'attendance':        None,   # placeholder — no Attendance model yet
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────

class ClassListView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/class_list.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        # All curriculum entries assigned to this lecturer this session
        all_units = (
            Curriculum.objects
            .filter(professor=lecturer, session=session)
            .select_related('syllabus__course', 'Tclass', 'session')
            .order_by('syllabus__course__course_code')
            if session else []
        )

        # Which curriculum is currently selected (query param or first)
        selected_id = request.GET.get('curriculum')
        selected = None

        if all_units:
            if selected_id:
                selected = next(
                    (u for u in all_units if str(u.record_id) == selected_id),
                    None
                )
            selected = selected or all_units[0]

        # ── build course selector list (lightweight — no student data) ────
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
                'curriculum':    unit,
                'slot':          slot,
                'total_enrolled': unit.enrollment_records.filter(
                    status='approved'
                ).count(),
            })

        # ── enrolled students for selected curriculum ─────────────────────
        student_rows = []
        stats = {}
        selected_slot = None

        if selected:
            enrollments = (
                Enrollment.objects
                .filter(curriculum=selected)
                .select_related('student__user')
                .order_by('student__registration_number')
            )

            # Fetch all Results for these students in this curriculum in one query
            enrolled_student_ids = list(
                enrollments.values_list('student_id', flat=True)
            )
            raw_results = (
                Result.objects
                .filter(
                    enrollment__curriculum=selected,
                    enrollment__student_id__in=enrolled_student_ids,
                )
                .values('enrollment__student_id', 'type', 'score')
            )

            # Collapse to {student_id: {cat: Decimal, exam: Decimal}}
            results_map: dict[str, dict] = {}
            for r in raw_results:
                sid = str(r['enrollment__student_id'])
                entry = results_map.setdefault(
                    sid, {'cat': Decimal('0'), 'exam': Decimal('0')})
                if r['type'] == 'C':
                    entry['cat'] = max(entry['cat'], r['score'])
                elif r['type'] == 'E':
                    entry['exam'] = max(entry['exam'], r['score'])

            student_rows = [
                _build_student_row(e, results_map) for e in enrollments
            ]

            # ── stats ────────────────────────────────────────────────────
            total = len(student_rows)
            approved = sum(
                1 for r in student_rows if r['status'] == 'approved')
            pending = sum(1 for r in student_rows if r['status'] == 'pending')
            rejected = sum(
                1 for r in student_rows if r['status'] == 'rejected')

            stats = {
                'total':    total,
                'approved': approved,
                'pending':  pending,
                'rejected': rejected,
            }

            selected_slot = (
                Timetable.objects
                .filter(curriculum=selected)
                .select_related('venue')
                .order_by('day', 'time_slot')
                .first()
            )

        context = {
            **self.get_context_data(),
            'session':       session,
            'unit_list':     unit_list,
            'selected':      selected,
            'selected_slot': selected_slot,
            'student_rows':  student_rows,
            'stats':         stats,
            'lecturer':      lecturer,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — student detail (for view modal)
# ─────────────────────────────────────────────────────────────────────────────

class StudentDetailAjaxView(RoleRequiredMixin, View):
    """
    GET /lecturer/class-list/student/<enrollment_id>/
    Returns JSON for the view-modal.
    """
    required_role = 'lecturer'

    def get(self, request, enrollment_id):
        try:
            enrollment = (
                Enrollment.objects
                .select_related('student__user', 'curriculum__syllabus__course')
                .get(record_id=enrollment_id)
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        # Verify this enrollment belongs to a curriculum this lecturer teaches
        lecturer = self.get_profile()
        if not enrollment.curriculum.professor.filter(pk=lecturer.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        student = enrollment.student
        user = student.user

        raw_results = Result.objects.filter(
            enrollment__curriculum=enrollment.curriculum,
            enrollment__student=student,
        ).values('type', 'title', 'score')

        results_out = [
            {
                'type':  r['type'],
                'title': r['title'],
                'score': str(r['score']),
            }
            for r in raw_results
        ]

        cat_total = sum(
            Decimal(r['score']) for r in raw_results if r['type'] == 'C'
        ) if raw_results else Decimal('0')
        exam_total = sum(
            Decimal(r['score']) for r in raw_results if r['type'] == 'E'
        ) if raw_results else Decimal('0')
        total = cat_total + exam_total

        return JsonResponse({
            'enrollment_id':   str(enrollment.record_id),
            'student_id':      str(student.record_id),
            'registration_no': student.registration_number,
            'full_name':       user.full_name,
            'email':           user.email,
            'school_email':    student.school_email,
            'status':          enrollment.status,
            'cat':             str(cat_total),
            'exam':            str(exam_total),
            'total':           str(total),
            'grade':           _grade_from_total(total) if total else '—',
            'results':         results_out,
            'course_code':     enrollment.curriculum.course.course_code,
            'course_name':     enrollment.curriculum.course.course_name,
        })
