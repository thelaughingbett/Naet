# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import Curriculum, Enrollment, Result, Session
from staffConsole.views.base import RoleRequiredMixin


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_unit_list(lecturer, session):
    """Return lightweight course selector data for all lecturer curricula."""
    units = (
        Curriculum.objects
        .filter(professor=lecturer, session=session)
        .select_related('syllabus__course', 'Tclass')
        .order_by('syllabus__course__course_code')
    )
    return [
        {
            'curriculum_id':  str(u.record_id),
            'code':           u.course.course_code,
            'name':           u.course.course_name,
            'class_name':     u.Tclass.class_name,
            'enrolled_count': u.enrollment_records.filter(status='approved').count(),
        }
        for u in units
    ], units


def _build_assessment_list(curriculum):
    """
    Assessments are virtual — they're (title, type) groupings of Result rows.
    Returns [ { title, type, type_display, score_count, total_students } ]
    sorted by earliest created_at within the group.
    """
    enrollments = list(
        Enrollment.objects.filter(curriculum=curriculum, status='approved')
    )
    total = len(enrollments)
    enrollment_ids = [e.record_id for e in enrollments]

    results = (
        Result.objects
        .filter(enrollment_id__in=enrollment_ids)
        .values('title', 'type')
        .distinct()
    )

    assessments = []
    type_display = dict(Result.type_result)
    for r in results:
        score_count = Result.objects.filter(
            enrollment_id__in=enrollment_ids,
            title=r['title'],
            type=r['type'],
        ).count()
        assessments.append({
            # synthetic stable ID
            'id':           f"{r['type']}::{r['title']}",
            'title':        r['title'],
            'type':         r['type'],
            'type_display': type_display.get(r['type'], r['type']),
            'score_count':  score_count,
            'total':        total,
        })
    return assessments


def _build_student_rows(curriculum, title, result_type):
    """
    For a given (title, type) assessment, return one row per approved enrollment.
    """
    enrollments = (
        Enrollment.objects
        .filter(curriculum=curriculum, status='approved')
        .select_related('student__user')
        .order_by('student__registration_number')
    )

    # Pre-fetch all result rows for this assessment in one query
    enrollment_ids = [e.record_id for e in enrollments]
    existing = {
        str(r.enrollment_id): r
        for r in Result.objects.filter(
            enrollment_id__in=enrollment_ids,
            title=title,
            type=result_type,
        )
    }

    rows = []
    for enr in enrollments:
        result = existing.get(str(enr.record_id))
        rows.append({
            'enrollment_id':   str(enr.record_id),
            'student_id':      str(enr.student.record_id),
            'registration_no': enr.student.registration_number,
            'full_name':       enr.student.user.full_name,
            'initials':        enr.student.user.initials,
            'score':           str(result.score) if result else '',
            'result_id':       str(result.record_id) if result else '',
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Page view
# ─────────────────────────────────────────────────────────────────────────────

class EnterResultsView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/enter_results.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        unit_list, _ = _build_unit_list(
            lecturer,
            session
        ) if session else ([], [])

        # Resolve the selected curriculum (query param or first)
        selected_id = request.GET.get('curriculum')
        selected = None

        if session and selected_id:
            try:
                selected = Curriculum.objects.select_related('syllabus__course', 'Tclass').get(
                    record_id=selected_id,
                    professor=lecturer,
                    session=session,
                )
            except Curriculum.DoesNotExist:
                pass

        if session and not selected and unit_list:
            try:
                selected = Curriculum.objects.select_related('syllabus__course', 'Tclass').get(
                    record_id=unit_list[0]['curriculum_id']
                )
            except Curriculum.DoesNotExist:
                pass

        assessments = _build_assessment_list(selected) if selected else []

        # Pre-select first assessment
        selected_assessment = None
        student_rows = []
        if assessments:
            selected_assessment = assessments[0]
            student_rows = _build_student_rows(
                selected,
                selected_assessment['title'],
                selected_assessment['type'],
            )

        # Stats
        total = len(student_rows)
        scored = sum(1 for r in student_rows if r['score'] != '')
        pending = total - scored
        avg = None
        scores = [Decimal(r['score']) for r in student_rows if r['score']]
        if scores:
            avg = round(sum(scores) / len(scores), 2)

        context = {
            **self.get_context_data(),
            'session':              session,
            'lecturer':             lecturer,
            'unit_list':            unit_list,
            'unit_list_json':       json.dumps(unit_list),
            'selected':             selected,
            'assessments':          assessments,
            'assessments_json':     json.dumps(assessments),
            'selected_assessment':  selected_assessment,
            'student_rows':         student_rows,
            'student_rows_json':    json.dumps(student_rows),
            'result_type_choices':  Result.type_result,
            'stats': {
                'total':   total,
                'scored':  scored,
                'pending': pending,
                'avg':     str(avg) if avg is not None else '—',
            },
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — switch assessment (returns student rows + stats)
# ─────────────────────────────────────────────────────────────────────────────

class AssessmentStudentsAjaxView(RoleRequiredMixin, View):
    """
    GET /lecturer/results/assessment-students/
        ?curriculum=<uuid>&title=<str>&type=<C|E|A>
    Returns student rows + stats for the requested assessment.
    """
    required_role = 'lecturer'

    def get(self, request):
        lecturer = self.get_profile()
        curriculum_id = request.GET.get('curriculum')
        title = request.GET.get('title', '').strip()
        result_type = request.GET.get('type', 'C')

        if not curriculum_id or not title:
            return JsonResponse({'error': 'Missing params'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id,
                professor=lecturer,
            )
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        rows = _build_student_rows(curriculum, title, result_type)

        scores = [Decimal(r['score']) for r in rows if r['score']]
        scored = len(scores)
        total = len(rows)
        avg = str(round(sum(scores) / scored, 2)) if scored else '—'

        return JsonResponse({
            'rows':    rows,
            'stats':   {
                'total':   total,
                'scored':  scored,
                'pending': total - scored,
                'avg':     avg,
            },
        })


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — save a single score
# ─────────────────────────────────────────────────────────────────────────────

class SaveScoreAjaxView(RoleRequiredMixin, View):
    """
    POST /lecturer/results/save-score/
    Body JSON: { enrollment_id, title, type, score }
    Creates or updates the Result row.
    Deletes the row if score is blank/null.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            enrollment_id = data['enrollment_id']
            title = data['title'].strip()
            result_type = data['type']
            raw_score = data.get('score', '')
        except (KeyError, json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        # Validate the enrollment belongs to a curriculum this lecturer teaches
        try:
            enrollment = (
                Enrollment.objects
                .select_related('student', 'curriculum')
                .get(record_id=enrollment_id)
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Enrollment not found'}, status=404)

        if not enrollment.curriculum.professor.filter(pk=lecturer.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        # Delete case
        if raw_score == '' or raw_score is None:
            Result.objects.filter(
                enrollment=enrollment,
                title=title,
                type=result_type,
            ).delete()
            return JsonResponse({'status': 'deleted'})

        # Parse score
        try:
            score = Decimal(str(raw_score))
        except InvalidOperation:
            return JsonResponse({'error': f'Invalid score: {raw_score}'}, status=400)

        if not (Decimal('0') <= score <= Decimal('100')):
            return JsonResponse({'error': 'Score must be 0–100'}, status=400)

        # Upsert
        result, created = Result.objects.update_or_create(
            enrollment=enrollment,
            title=title,
            type=result_type,
            defaults={
                'score':      score,
                'entered_by': request.user,
            },
        )

        return JsonResponse({
            'status':    'created' if created else 'updated',
            'result_id': str(result.record_id),
            'score':     str(result.score),
        })


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — add assessment (just validates; rows are created on first score save)
# ─────────────────────────────────────────────────────────────────────────────

class AddAssessmentAjaxView(RoleRequiredMixin, View):
    """
    POST /lecturer/results/add-assessment/
    Body JSON: { curriculum_id, title, type }
    Returns the updated assessment list for this curriculum.
    Assessments are (title, type) combinations — they don't have their own DB row.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            title = data['title'].strip()
            result_type = data['type']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)

        valid_types = [t[0] for t in Result.type_result]
        if result_type not in valid_types:
            return JsonResponse({'error': f'Invalid type. Choose from {valid_types}'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer
            )
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        # Check for duplicate
        enrollment_ids = list(
            Enrollment.objects.filter(
                curriculum=curriculum,
                status='approved'
            ).values_list('record_id', flat=True)
        )
        if Result.objects.filter(
            enrollment_id__in=enrollment_ids,
            title=title,
            type=result_type,
        ).exists():
            return JsonResponse({
                'error': f'An assessment called "{title}" ({result_type}) already exists for this course.'
            }, status=400)

        # Return updated assessment list (new one won't appear until first score is saved,
        # so we return a synthetic entry too)
        assessments = _build_assessment_list(curriculum)
        type_display = dict(Result.type_result)
        assessments.append({
            'id':           f'{result_type}::{title}',
            'title':        title,
            'type':         result_type,
            'type_display': type_display.get(result_type, result_type),
            'score_count':  0,
            'total':        len(enrollment_ids),
            'new':          True,
        })

        return JsonResponse({'assessments': assessments})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — delete assessment (deletes all Result rows for title+type)
# ─────────────────────────────────────────────────────────────────────────────

class DeleteAssessmentAjaxView(RoleRequiredMixin, View):
    """
    DELETE /lecturer/results/delete-assessment/
    Body JSON: { curriculum_id, title, type }
    """
    required_role = 'lecturer'

    def delete(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            title = data['title']
            result_type = data['type']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer
            )
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        enrollment_ids = list(
            Enrollment.objects.filter(
                curriculum=curriculum, status='approved'
            ).values_list('record_id', flat=True)
        )

        with transaction.atomic():
            deleted_count, _ = Result.objects.filter(
                enrollment_id__in=enrollment_ids,
                title=title,
                type=result_type,
            ).delete()

        assessments = _build_assessment_list(curriculum)
        return JsonResponse({'deleted': deleted_count, 'assessments': assessments})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — bulk save (save all + import CSV)
# ─────────────────────────────────────────────────────────────────────────────

class BulkSaveScoresAjaxView(RoleRequiredMixin, View):
    """
    POST /lecturer/results/bulk-save/
    Body JSON: { curriculum_id, title, type, scores: [ {enrollment_id, score}, … ] }
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            title = data['title'].strip()
            result_type = data['type']
            scores = data['scores']   # [{enrollment_id, score}, …]
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer
            )
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        # Build enrollment lookup for this curriculum
        enrollments = {
            str(e.record_id): e
            for e in Enrollment.objects.filter(
                curriculum=curriculum, status='approved'
            ).select_related('student')
        }

        saved = 0
        errors = []

        with transaction.atomic():
            for item in scores:
                eid = str(item.get('enrollment_id', ''))
                raw_score = item.get('score', '')

                enrollment = enrollments.get(eid)
                if not enrollment:
                    errors.append(f'Unknown enrollment {eid}')
                    continue

                if raw_score == '' or raw_score is None:
                    Result.objects.filter(
                        enrollment=enrollment, title=title, type=result_type
                    ).delete()
                    continue

                try:
                    score = Decimal(str(raw_score))
                    if not (Decimal('0') <= score <= Decimal('100')):
                        raise ValueError()
                except (InvalidOperation, ValueError):
                    errors.append(
                        f'Invalid score {raw_score} for {enrollment.student.registration_number}')
                    continue

                result, created = Result.objects.update_or_create(
                    enrollment=enrollment,
                    title=title,
                    type=result_type,
                    defaults={
                        'score':      score,
                        'entered_by': request.user,
                    },
                )
                saved += 1

        return JsonResponse({'saved': saved, 'errors': errors})


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV template
# ─────────────────────────────────────────────────────────────────────────────

class ExportTemplateView(RoleRequiredMixin, View):
    """
    GET /lecturer/results/export-template/?curriculum=<uuid>&title=<str>&type=<C|E|A>
    Returns a CSV with Student ID, Name, Score pre-filled where scores exist.
    """
    required_role = 'lecturer'

    def get(self, request):
        lecturer = self.get_profile()
        curriculum_id = request.GET.get('curriculum')
        title = request.GET.get('title', 'Results')
        result_type = request.GET.get('type', 'C')

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer
            )
        except Curriculum.DoesNotExist:
            return HttpResponse('Not found', status=404)

        rows = _build_student_rows(curriculum, title, result_type)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student ID', 'Name', 'Score'])
        for row in rows:
            writer.writerow(
                [row['registration_no'], row['full_name'], row['score']])

        filename = f"{curriculum.course.course_code}_{title}_{result_type}_template.csv"
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
