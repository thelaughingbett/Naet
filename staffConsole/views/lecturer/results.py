# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from base.modules.academics.grading_service import GradingService, PREVIEW, FINALIZE
import csv
import io
import json
import math
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from base.models import (
    Curriculum,
    Enrollment,
    Result,
    Session,
    WeightingScheme,
    RESULT_TYPE_CHOICES,
)
from staffConsole.views.base import RoleRequiredMixin


PAGE_SIZE = 10          # hard cap: never more than ten students per page
LOCKED_MSG = 'Grades for this course have been locked and transmitted.'
# Result states that count towards a grade at lock time. Exam/Project results
# are moved draft -> submitted *before* finalizing, so 'submitted' must count.
FINALIZE_STATES = FINALIZE

MIN_READY_PERCENT = 83


# ─────────────────────────────────────────────────────────────────────────────
# Grading context — loaded ONCE per request, shared by rows / previews / stats
# ─────────────────────────────────────────────────────────────────────────────

def _safe(fn):
    try:
        return fn()
    except (ValidationError, AttributeError, ObjectDoesNotExist):
        return None


def _js(obj):
    """
    json.dumps for embedding inside a <script> block via |safe. Escapes the
    characters that could otherwise close the script tag or open an HTML
    comment if a name/title ever contains them.
    """
    return (json.dumps(obj)
            .replace('<', '\\u003c')
            .replace('>', '\\u003e')
            .replace('&', '\\u0026'))


def _preview_dict(o):
    """EnrollmentOutcome -> the {final, letter, complete} shape the UI uses."""
    return {
        'final':    None if o.score is None else str(o.score),
        'letter':   o.grade_letter or '',
        'complete': o.complete,
    }


def _load(curriculum):
    """Everything the grading previews need, loaded once per request."""
    svc = GradingService()
    enrollments = list(
        Enrollment.objects
        .filter(curriculum=curriculum, status='approved')
        .select_related('student__user', 'student__class_entered',
                        'curriculum__course')
        .order_by('student__registration_number')
    )
    policy = svc.policy_for(curriculum)
    by_enr = defaultdict(
        list, svc.fetch_results([e.record_id for e in enrollments], PREVIEW))

    previews = {
        str(e.record_id): _preview_dict(
            svc.outcome(e, results=by_enr[str(e.record_id)], states=PREVIEW))
        for e in enrollments
    }
    return {
        'svc':         svc,
        'policy':      policy,
        'enrollments': enrollments,
        'results':     by_enr,
        'previews':    previews,
        'scheme':      policy.scheme,
        'scale':       policy.scale,
        'components':  list(policy.components),
    }


def _rows(ctx, title, result_type):
    """One row per approved enrollment for the (title, type) assessment."""
    rows = []
    for enr in ctx['enrollments']:
        eid = str(enr.record_id)
        res = next(
            (r for r in ctx['results'][eid]
             if r.title == title and r.type == result_type),
            None,
        )
        rows.append({
            'enrollment_id':   eid,
            'student_id':      str(enr.student.record_id),
            'registration_no': enr.student.registration_number,
            'full_name':       enr.student.user.full_name,
            'initials':        enr.student.user.initials,
            'class_name':      enr.student.class_entered.class_name,
            'score':           str(res.score) if res else '',
            'result_id':       str(res.record_id) if res else '',
            'graded':          enr.graded_at is not None,
            **ctx['previews'][eid],
        })
    return rows


def _readiness(ctx):
    """
    Finalized + complete-but-not-yet-finalized students vs the required share
    of the WHOLE approved class. Integer ceil so 83% of 30 = 25, never 24.9.
    """
    enrollments = ctx['enrollments']
    total = len(enrollments)
    finalized = ready = 0
    for e in enrollments:
        if e.graded_at is not None:
            finalized += 1
        elif ctx['previews'][str(e.record_id)]['complete']:
            ready += 1
    required = -(-total * MIN_READY_PERCENT // 100)
    return {
        'finalized':    finalized,
        'ready':        ready,                      # complete, awaiting finalize
        'incomplete':   total - finalized - ready,
        'required':     required,
        'min_percent':  MIN_READY_PERCENT,
        'can_finalize': ready > 0 and (finalized + ready) >= required,
    }


def _stats(ctx, rows):
    total = len(ctx['enrollments'])
    scored = sum(1 for r in rows if r['score'] != '')
    finals = [Decimal(p['final'])
              for p in ctx['previews'].values() if p['complete']]
    avg = round(sum(finals) / len(finals), 2) if finals else None
    return {
        'total':   total,
        'scored':  scored,
        'pending': total - scored,
        'avg':     str(avg) if avg is not None else '—',
        **_readiness(ctx),
    }


def _paginate(rows, q='', klass='', status='', page=1):
    q = (q or '').lower().strip()

    def ok(r):
        if q and q not in r['full_name'].lower() \
                and q not in r['registration_no'].lower():
            return False
        if klass and r['class_name'] != klass:
            return False
        if status == 'entered' and r['score'] == '':
            return False
        if status == 'not_entered' and r['score'] != '':
            return False
        return True

    filtered = [r for r in rows if ok(r)]
    total = len(filtered)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page = min(max(page, 1), pages)

    start = (page - 1) * PAGE_SIZE
    chunk = filtered[start:start + PAGE_SIZE]
    return chunk, {
        'page':      page,
        'pages':     pages,
        'total':     total,
        'page_size': PAGE_SIZE,
        'start':     start + 1 if total else 0,
        'end':       start + len(chunk),
    }


def _payload(curriculum, title, result_type, q='', klass='', status='', page=1):
    ctx = _load(curriculum)
    rows = _rows(ctx, title, result_type) if title else []
    chunk, pagination = _paginate(rows, q, klass, status, page)
    return {
        'rows':       chunk,
        'pagination': pagination,
        'stats':      _stats(ctx, rows),
        'classes':    sorted({e.student.class_entered.class_name
                              for e in ctx['enrollments']}),
    }


def _agg_label(c):
    """Short human label for a WeightingComponent's aggregation strategy."""
    A = c.Aggregation
    if c.aggregation == A.BEST_N:
        return f'Best {c.n_count} of {c.expected_count}'
    if c.aggregation == A.LATEST_N:
        return f'Latest {c.n_count} of {c.expected_count}'
    return {
        A.AVERAGE_ALL: 'Average all',
        A.SUM:         'Sum all',
        A.LATEST:      'Latest only',
    }.get(c.aggregation, c.get_aggregation_display())


def _fmt_weight(w):
    return format(w.normalize(), 'f')


def _scheme_summary(curriculum, scheme=None):
    """The curriculum's ACTIVE weighting scheme + scale name, for the policy card."""
    scheme = scheme or _safe(curriculum.get_weighting_scheme)
    scale = _safe(curriculum.course.get_grading_scale)
    if not scheme:
        return None

    return {
        'id':         str(scheme.record_id),
        'name':       scheme.name,
        'scale_name': scale.name if scale else '—',
        'components': [
            {
                'label':       c.get_result_type_display(),
                'result_type': c.result_type,
                'weight':      _fmt_weight(c.weight_percent),
                'aggregation': _agg_label(c),
            }
            for c in scheme.components.all().order_by('-weight_percent')
        ],
    }


def _fmt_points(gp):
    s = f'{gp:.2f}'
    return s[:-1] if s.endswith('0') else s      # 4.00 -> 4.0, 3.67 stays


def _scale_summary(curriculum):
    """
    The read-only grading bands (score -> letter / grade points). Ranges are
    shown to two decimals because finals are quantized to 0.01: a 69.5 final
    really does earn the 60+ band, so '60 – 69' would be misleading.
    """
    scale = _safe(curriculum.course.get_grading_scale)
    if not scale:
        return None

    bands = sorted(scale.bands.all(), key=lambda b: -b.min_score)
    out = []
    for i, b in enumerate(bands):
        if i == 0:
            rng = f'{b.min_score} – 100'
        else:
            rng = f'{b.min_score} – {bands[i - 1].min_score - 0.01:.2f}'
        label = b.label or str(b.grade_points)
        key = label[:1].upper()
        out.append({
            'label':  label,
            'key':    key if key in 'ABCDF' and key else 'C',
            'range':  rng,
            'points': _fmt_points(b.grade_points),
        })
    return {'name': scale.name, 'bands': out}


def _scheme_options(curriculum):
    """
    Schemes a lecturer may switch this curriculum to. A scheme whose weights
    don't sum to 100% is never offered (it would grade nobody correctly) —
    except the one already active, so the modal can still show "Current".

    'is_default' marks the COURSE's own default (what you get with no
    override), not the institution-wide WeightingScheme.is_default flag.
    """
    active = _safe(curriculum.get_weighting_scheme)
    active_id = str(active.record_id) if active else None
    course_default = _safe(curriculum.course.get_weighting_scheme)
    default_id = str(course_default.record_id) if course_default else None

    options = []
    for sch in WeightingScheme.objects.prefetch_related('components').order_by('name'):
        comps = sorted(sch.components.all(), key=lambda c: -c.weight_percent)
        sid = str(sch.record_id)
        if not comps:
            continue
        if sum(c.weight_percent for c in comps) != Decimal('100') and sid != active_id:
            continue
        options.append({
            'id':          sid,
            'name':        sch.name,
            'description': ' · '.join(
                f'{c.get_result_type_display()}: {_agg_label(c)}' for c in comps),
            'is_current':  sid == active_id,
            'is_default':  sid == default_id,
            'components':  [
                {'label': c.get_result_type_display(),
                 'weight': _fmt_weight(c.weight_percent)}
                for c in comps
            ],
        })
    return options


def _policy(curriculum):
    """Everything the grading-policy card + Change-weighting modal render from."""
    return {
        'scheme':  _scheme_summary(curriculum),
        'scale':   _scale_summary(curriculum),
        'options': _scheme_options(curriculum),
    }


def _scheme_impact(curriculum, candidate):
    """
    Server-side "what would change" for switching to `candidate`. The browser
    only ever holds one page of ten students, so the comparison runs here over
    ALL approved enrollments using the real aggregation logic.
    """
    ctx = _load(curriculum)
    svc = ctx['svc']
    new_policy = svc.policy_for(curriculum, scheme=candidate)

    changed = improved = dropped = unchanged = 0
    became_incomplete = became_complete = 0
    for e in ctx['enrollments']:
        eid = str(e.record_id)
        old = ctx['previews'][eid]
        new = _preview_dict(svc.evaluate(
            new_policy, ctx['results'][eid], e.curriculum.course.credits))

        if old['complete'] and not new['complete']:
            became_incomplete += 1
        elif not old['complete'] and new['complete']:
            became_complete += 1
        elif old['complete'] and new['complete']:
            o, n = Decimal(old['final']), Decimal(new['final'])
            if o == n:
                unchanged += 1
            else:
                changed += 1
                if n > o:
                    improved += 1
                else:
                    dropped += 1

    return {
        'total':             len(ctx['enrollments']),
        'changed':           changed,
        'improved':          improved,
        'dropped':           dropped,
        'unchanged':         unchanged,
        'became_incomplete': became_incomplete,
        'became_complete':   became_complete,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Other helpers
# ─────────────────────────────────────────────────────────────────────────────
def _build_unit_list(lecturer, session):
    units = (
        Curriculum.objects
        .filter(professor=lecturer, session=session)
        .select_related('course')
        .prefetch_related('classes')
        .order_by('course__course_code')
    )
    return [
        {
            'curriculum_id':  str(u.record_id),
            'code':           u.course.course_code,
            'name':           u.course.course_name,
            'class_names':    ", ".join(u.classes.values_list('class_name', flat=True)),
            'enrolled_count': u.enrollment_records.filter(status='approved').count(),
        }
        for u in units
    ], units


def _build_assessment_list(curriculum):
    """Assessments are virtual — (title, type) groupings of Result rows."""
    enrollment_ids = list(
        Enrollment.objects.filter(curriculum=curriculum, status='approved')
        .values_list('record_id', flat=True)
    )
    total = len(enrollment_ids)

    results = (
        Result.objects
        .filter(enrollment_id__in=enrollment_ids)
        .values('title', 'type')
        .annotate(score_count=Count('record_id'))
    )
    type_display = dict(RESULT_TYPE_CHOICES)
    return [
        {
            'id':           f"{r['type']}::{r['title']}",
            'title':        r['title'],
            'type':         r['type'],
            'type_display': type_display.get(r['type'], r['type']),
            'score_count':  r['score_count'],
            'total':        total,
        }
        for r in results
    ]


def _build_student_rows(curriculum, title, result_type):
    return _rows(_load(curriculum), title, result_type)


def _lock_info(curriculum):
    """
    No separate lock record: a curriculum is LOCKED once every approved
    enrollment has been finalized (Enrollment.graded_at is set — that is
    exactly what Lock & Transmit does). locked_at is the latest graded_at.
    """
    agg = (
        Enrollment.objects
        .filter(curriculum=curriculum, status='approved')
        .aggregate(total=Count('record_id'),
                   graded=Count('graded_at'),
                   at=Max('graded_at'))
    )
    locked = agg['total'] > 0 and agg['graded'] == agg['total']
    return locked, (agg['at'] if locked else None)


def _locked_response(curriculum):
    if _lock_info(curriculum)[0]:
        return JsonResponse({'error': LOCKED_MSG}, status=403)
    return None


def _get_deadline(session):
    """Assumes a nullable `results_deadline` DateTimeField on Session."""
    deadline_dt = getattr(session, 'results_deadline', None)
    if not deadline_dt:
        return None
    days = (timezone.localtime(deadline_dt).date() - timezone.localdate()).days
    return {'date': deadline_dt, 'days_remaining': days}


def _get_last_saved(curriculum):
    enrollment_ids = list(
        Enrollment.objects.filter(curriculum=curriculum, status='approved')
        .values_list('record_id', flat=True)
    )
    return (
        Result.history
        .filter(enrollment_id__in=enrollment_ids)
        .order_by('-history_date')
        .values_list('history_date', flat=True)
        .first()
    )


def _fmt_dt(dt):
    return timezone.localtime(dt).strftime('%b %d, %Y, %I:%M %p')


def _save_response(curriculum, enrollment, title, result_type, **extra):
    """Fresh preview for the edited student + fresh stats, after any write."""
    ctx = _load(curriculum)
    return {
        'preview': ctx['previews'][str(enrollment.record_id)],
        'stats':   _stats(ctx, _rows(ctx, title, result_type)),
        **extra,
    }


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
            lecturer, session) if session else ([], [])

        selected_id = request.GET.get('curriculum')
        selected = None
        base_qs = (
            Curriculum.objects
            .select_related('course')
            .prefetch_related('classes')
        )

        if session and selected_id:
            try:
                selected = base_qs.get(
                    record_id=selected_id, professor=lecturer, session=session,
                )
            except (Curriculum.DoesNotExist, ValueError, ValidationError):
                pass

        if session and not selected and unit_list:
            try:
                selected = base_qs.get(
                    record_id=unit_list[0]['curriculum_id'],
                    professor=lecturer, session=session,
                )
            except Curriculum.DoesNotExist:
                pass

        assessments = _build_assessment_list(selected) if selected else []
        selected_assessment = assessments[0] if assessments else None

        empty = {
            'rows': [], 'classes': [],
            'pagination': {
                'page': 1,
                'pages': 1,
                'total': 0,
                'page_size': PAGE_SIZE,
                'start': 0,
                'end': 0
            },
            'stats': {
                'total': 0,
                'scored': 0,
                'pending': 0,
                'avg': '—',
                'ready': 0,
                'incomplete': 0,
                'finalized': 0,
                'required': 0,
                'min_percent': MIN_READY_PERCENT,
                'can_finalize': False
            },
        }
        payload = empty
        if selected:
            payload = _payload(
                selected,
                selected_assessment['title'] if selected_assessment else '',
                selected_assessment['type'] if selected_assessment else 'C',
            )

        locked, locked_at = _lock_info(selected) if selected else (False, None)

        context = {
            **self.get_context_data(),
            'session':              session,
            'lecturer':             lecturer,
            'unit_list':            unit_list,
            'unit_list_json':       _js(unit_list),
            'selected':             selected,
            'assessments':          assessments,
            'selected_assessment':  selected_assessment,
            'result_type_choices':  RESULT_TYPE_CHOICES,
            'initial_payload_json': _js(payload),
            'stats':                payload['stats'],
            # Grading policy card + Change-weighting modal (scheme, bands, options)
            'grading_policy_json':  _js(_policy(selected) if selected else
                                        {'scheme': None, 'scale': None, 'options': []}),
            'deadline':             _get_deadline(session) if (session and selected) else None,
            'last_saved':           _get_last_saved(selected) if selected else None,
            'grades_locked':        locked,
            'locked_at':            locked_at,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — one page of students (+ stats, classes)
# ─────────────────────────────────────────────────────────────────────────────
class AssessmentStudentsAjaxView(RoleRequiredMixin, View):
    """
    GET /staff/lecturer/results/assessment-students/
        ?curriculum=<uuid>&title=<str>&type=<C|E|P|A|Q|PR>
        &page=<n>&q=<str>&class=<str>&status=<entered|not_entered>
    Returns at most PAGE_SIZE (10) rows.
    """
    required_role = 'lecturer'

    def get(self, request):
        lecturer = self.get_profile()
        curriculum_id = request.GET.get('curriculum')
        if not curriculum_id:
            return JsonResponse({'error': 'Missing params'}, status=400)

        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=curriculum_id, professor=lecturer,
            )
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({'error': 'Not found'}, status=404)

        return JsonResponse(_payload(
            curriculum,
            request.GET.get('title', '').strip(),
            request.GET.get('type', 'C'),
            q=request.GET.get('q', ''),
            klass=request.GET.get('class', ''),
            status=request.GET.get('status', ''),
            page=request.GET.get('page', 1),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — save a single score
# ─────────────────────────────────────────────────────────────────────────────
class SaveScoreAjaxView(RoleRequiredMixin, View):
    """
    POST /staff/lecturer/results/save-score/
    Body JSON: { enrollment_id, title, type, score }
    Blank score deletes the row. Returns the student's fresh final preview
    and fresh stats so the UI never has to recompute grading client-side.
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

        try:
            enrollment = (
                Enrollment.objects
                .select_related('student', 'curriculum__course')
                .get(record_id=enrollment_id)
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Enrollment not found'}, status=404)

        curriculum = enrollment.curriculum
        if not curriculum.professor.filter(pk=lecturer.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        locked = _locked_response(curriculum)
        if locked:
            return locked

        if enrollment.graded_at is not None:      # this student's grade is frozen
            return JsonResponse({'error': LOCKED_MSG}, status=403)

        if raw_score == '' or raw_score is None:
            Result.objects.filter(
                enrollment=enrollment, title=title, type=result_type,
            ).delete()
            return JsonResponse(_save_response(
                curriculum, enrollment, title, result_type, status='deleted'))

        try:
            score = Decimal(str(raw_score))
        except InvalidOperation:
            return JsonResponse({'error': f'Invalid score: {raw_score}'}, status=400)

        if not (Decimal('0') <= score <= Decimal('100')):
            return JsonResponse({'error': 'Score must be 0–100'}, status=400)

        result, created = Result.objects.update_or_create(
            enrollment=enrollment, title=title, type=result_type,
            defaults={'score': score, 'entered_by': request.user},
        )
        return JsonResponse(_save_response(
            curriculum, enrollment, title, result_type,
            status='created' if created else 'updated',
            result_id=str(result.record_id),
            score=str(result.score),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — add assessment (validation only; rows are created on first save)
# ─────────────────────────────────────────────────────────────────────────────
class AddAssessmentAjaxView(RoleRequiredMixin, View):
    """POST /staff/lecturer/results/add-assessment/  { curriculum_id, title, type }"""
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            title = data['title'].strip()
            result_type = data['type']
        except (KeyError, json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)

        valid_types = [t[0] for t in RESULT_TYPE_CHOICES]
        if result_type not in valid_types:
            return JsonResponse({'error': f'Invalid type. Choose from {valid_types}'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer)
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        locked = _locked_response(curriculum)
        if locked:
            return locked

        enrollment_ids = list(
            Enrollment.objects.filter(curriculum=curriculum, status='approved')
            .values_list('record_id', flat=True)
        )
        if Result.objects.filter(
            enrollment_id__in=enrollment_ids, title=title, type=result_type,
        ).exists():
            return JsonResponse({
                'error': f'An assessment called "{title}" ({result_type}) already exists for this course.'
            }, status=400)

        assessments = _build_assessment_list(curriculum)
        assessments.append({
            'id':           f'{result_type}::{title}',
            'title':        title,
            'type':         result_type,
            'type_display': dict(RESULT_TYPE_CHOICES).get(result_type, result_type),
            'score_count':  0,
            'total':        len(enrollment_ids),
            'new':          True,
        })
        return JsonResponse({'assessments': assessments})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — delete assessment
# ─────────────────────────────────────────────────────────────────────────────
class DeleteAssessmentAjaxView(RoleRequiredMixin, View):
    """DELETE /staff/lecturer/results/delete-assessment/  { curriculum_id, title, type }"""
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
                record_id=curriculum_id, professor=lecturer)
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        locked = _locked_response(curriculum)
        if locked:
            return locked

        enrollment_ids = list(
            Enrollment.objects.filter(curriculum=curriculum, status='approved')
            .values_list('record_id', flat=True)
        )
        if Enrollment.objects.filter(
            curriculum=curriculum, status='approved', graded_at__isnull=False,
        ).exists():
            return JsonResponse({
                'error': 'Some students are already graded; this assessment can no longer be deleted.'
            }, status=403)

        with transaction.atomic():
            deleted_count, _ = Result.objects.filter(
                enrollment_id__in=enrollment_ids, title=title, type=result_type,
            ).delete()

        return JsonResponse({
            'deleted': deleted_count,
            'assessments': _build_assessment_list(curriculum),
        })


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — bulk save (Save All + Import CSV)
# ─────────────────────────────────────────────────────────────────────────────
class BulkSaveScoresAjaxView(RoleRequiredMixin, View):
    """
    POST /staff/lecturer/results/bulk-save/
    Body JSON: { curriculum_id, title, type,
                 scores: [ {enrollment_id | registration_no, score}, … ] }
    registration_no lets CSV import work across ALL students even though the
    browser only ever holds one page of ten.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            title = data['title'].strip()
            result_type = data['type']
            scores = data['scores']
        except (KeyError, json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id, professor=lecturer)
        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        locked = _locked_response(curriculum)
        if locked:
            return locked

        enrollments = list(
            Enrollment.objects.filter(curriculum=curriculum, status='approved')
            .select_related('student')
        )
        by_id = {str(e.record_id): e for e in enrollments}
        by_reg = {e.student.registration_number.lower(): e for e in enrollments}

        saved = 0
        errors = []

        with transaction.atomic():
            for item in scores:
                eid = str(item.get('enrollment_id', '') or '')
                reg = str(item.get('registration_no', '') or '').lower()
                enrollment = by_id.get(eid) or by_reg.get(reg)
                if not enrollment:
                    errors.append(f'Unknown student {eid or reg}')
                    continue

                if enrollment.graded_at is not None:
                    errors.append(
                        f'{enrollment.student.registration_number} is already graded')
                    continue

                raw_score = item.get('score', '')
                if raw_score == '' or raw_score is None:
                    Result.objects.filter(
                        enrollment=enrollment, title=title, type=result_type,
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

                Result.objects.update_or_create(
                    enrollment=enrollment, title=title, type=result_type,
                    defaults={'score': score, 'entered_by': request.user},
                )
                saved += 1

        return JsonResponse({'saved': saved, 'errors': errors})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — Change weighting scheme: impact preview + apply
# ─────────────────────────────────────────────────────────────────────────────
def _get_scheme(scheme_id):
    try:
        return WeightingScheme.objects.prefetch_related('components').get(
            record_id=scheme_id)
    except (WeightingScheme.DoesNotExist, ValueError, ValidationError):
        return None


class SchemeImpactAjaxView(RoleRequiredMixin, View):
    """
    GET /staff/lecturer/results/scheme-impact/?curriculum=<uuid>&scheme=<uuid>
    Read-only what-if: how many students' finals would move if this
    curriculum switched to `scheme`. Nothing is written.
    """
    required_role = 'lecturer'

    def get(self, request):
        lecturer = self.get_profile()
        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=request.GET.get('curriculum'), professor=lecturer)
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({'error': 'Not found'}, status=404)

        candidate = _get_scheme(request.GET.get('scheme'))
        if candidate is None:
            return JsonResponse({'error': 'Scheme not found'}, status=404)

        return JsonResponse(_scheme_impact(curriculum, candidate))


class ApplySchemeAjaxView(RoleRequiredMixin, View):
    """
    POST /staff/lecturer/results/apply-scheme/   { curriculum_id, scheme_id }

    Points Curriculum.weighting_scheme_override at the chosen scheme, so
    Curriculum.get_weighting_scheme() — and therefore every preview AND
    Enrollment.finalize_grade() — uses it from now on.

    Refused once any student on the curriculum has been finalized: grades
    already frozen under the old scheme (Enrollment.weighting_scheme_used)
    must not be mixed with new ones. The curriculum row is locked for the
    check + write so it can't race a Lock & Transmit from another tab.
    Returns the refreshed policy so the card/modal re-render without a reload.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            scheme_id = data['scheme_id']
        except (KeyError, json.JSONDecodeError, TypeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=curriculum_id,
                professor=lecturer
            )
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({'error': 'Not found'}, status=404)

        scheme = _get_scheme(scheme_id)
        if scheme is None:
            return JsonResponse({'error': 'Scheme not found'}, status=404)

        if not scheme.components.exists():
            return JsonResponse(
                {'error': f'"{scheme.name}" has no components configured.'}, status=400)
        try:
            scheme.validate_weights_sum_to_100()
        except ValidationError as exc:
            return JsonResponse({'error': "; ".join(exc.messages)}, status=400)

        with transaction.atomic():
            locked_row = (Curriculum.objects.select_for_update()
                          .get(record_id=curriculum.record_id))
            if Enrollment.objects.filter(
                curriculum=locked_row, status='approved', graded_at__isnull=False,
            ).exists():
                return JsonResponse({'error': LOCKED_MSG}, status=403)

            locked_row.weighting_scheme_override = scheme
            locked_row._change_reason = (
                f'Weighting scheme changed to "{scheme.name}" by {request.user}')
            locked_row.save(update_fields=['weighting_scheme_override'])

        curriculum.refresh_from_db()
        return JsonResponse(_policy(curriculum))


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — LOCK & TRANSMIT
# ─────────────────────────────────────────────────────────────────────────────
class _AlreadyLocked(Exception):
    pass


class _FinalizeFailed(Exception):
    def __init__(self, enrollment):
        self.enrollment = enrollment


class LockTransmitAjaxView(RoleRequiredMixin, View):
    """
    POST /staff/lecturer/results/lock-transmit/
    Body JSON: { curriculum_id, certified: true }

    Locking IS finalizing — there is no separate lock record. One transaction,
    any failure rolls everything back:

      1. Gate: every approved student must have a complete final preview.
      2. Row-lock the enrollments (a double-click / second tab serialises here
         and the loser sees them already graded -> 409).
      3. Exam/Project results draft -> submitted (the HOD approval queue).
      4. Enrollment.finalize_grade() for each student, counting 'submitted'
         results. This sets graded_at, which is what _lock_info() reads.

    Who/when is audited by Enrollment's HistoricalRecords (history_user).
    Response: { transmitted_at, submitted_for_approval, finalized }
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
        except (KeyError, json.JSONDecodeError, TypeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        # Server-side enforcement of the FERPA checkbox.
        if data.get('certified') is not True:
            return JsonResponse(
                {
                    'error': 'You must accept the certification before locking.'
                },
                status=400)

        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=curriculum_id,
                professor=lecturer
            )
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({'error': 'Not found'}, status=404)

        if _lock_info(curriculum)[0]:
            return JsonResponse({'error': LOCKED_MSG}, status=409)

        # 1. Gate
        ctx = _load(curriculum)
        enrollments = ctx['enrollments']
        if not enrollments:
            return JsonResponse(
                {'error': 'There are no approved students to transmit.'}, status=400)
        if not ctx['components']:
            return JsonResponse(
                {'error': 'No weighting scheme is configured for this course.'},
                status=400)

        r = _readiness(ctx)
        total = len(enrollments)
        if r['ready'] == 0:
            return JsonResponse(
                {'error': 'No students are ready to finalize yet.'}, status=400)
        complete = r['finalized'] + r['ready']
        if complete < r['required']:
            return JsonResponse({
                'error': f'At least {MIN_READY_PERCENT}% of the class must have '
                f'complete results before submitting '
                f'({complete} of {total} complete, {r["required"]} needed).'
            }, status=400)

        ready_ids = [
            e.record_id for e in enrollments
            if e.graded_at is None and ctx['previews'][str(e.record_id)]['complete']
        ]

        submitted = finalized = 0
        try:
            with transaction.atomic():
                # 2. Serialise concurrent attempts; only still-ungraded rows.
                rows = list(
                    Enrollment.objects
                    .select_for_update(of=('self',))
                    .select_related('curriculum__course')
                    .filter(record_id__in=ready_ids, graded_at__isnull=True)
                )
                if not rows:
                    raise _AlreadyLocked()
                locked_ids = [e.record_id for e in rows]

                # 3. Exams / Projects -> submitted, ready students only.
                for res in Result.objects.filter(
                    enrollment_id__in=locked_ids,
                    type__in=Enrollment.FINAL_RESULT_TYPES,
                    state='draft',
                ):
                    res.state = 'submitted'
                    res.save()
                    submitted += 1

                # 4. Freeze grades for ready students only.
                for enr in rows:
                    if not ctx['svc'].finalize(enr, states=FINALIZE_STATES):
                        raise _FinalizeFailed(enr)
                    finalized += 1

        except _AlreadyLocked:
            return JsonResponse({'error': LOCKED_MSG}, status=409)
        except _FinalizeFailed as exc:
            return JsonResponse({
                'error': 'Could not finalize the grade for '
                         f'{exc.enrollment.student.registration_number}. '
                         'Nothing was locked.'
            }, status=400)
        except ValidationError as exc:
            return JsonResponse(
                {'error': f'Grading configuration error: {"; ".join(exc.messages)}'},
                status=400)

        pending = total - r['finalized'] - finalized
        return JsonResponse({
            'transmitted_at':         _fmt_dt(timezone.now()),
            'submitted_for_approval': submitted,
            'finalized':              finalized,
            'pending':                pending,
            'fully_locked':           pending == 0,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV template (read-only — stays available after locking)
# ─────────────────────────────────────────────────────────────────────────────
# class ExportTemplateView(RoleRequiredMixin, View):
#     """GET /staff/lecturer/results/export-template/?curriculum=&title=&type="""
#     required_role = 'lecturer'

#     def get(self, request):
#         lecturer = self.get_profile()
#         curriculum_id = request.GET.get('curriculum')
#         title = request.GET.get('title', 'Results')
#         result_type = request.GET.get('type', 'C')

#         try:
#             curriculum = Curriculum.objects.select_related('course').get(
#                 record_id=curriculum_id, professor=lecturer)
#         except (Curriculum.DoesNotExist, ValueError, ValidationError):
#             return HttpResponse('Not found', status=404)

#         rows = _build_student_rows(curriculum, title, result_type)

#         output = io.StringIO()
#         writer = csv.writer(output)
#         writer.writerow(['Student ID', 'Name', 'Score'])
#         for row in rows:
#             writer.writerow(
#                 [row['registration_no'], row['full_name'], row['score']])

#         filename = f"{curriculum.course.course_code}_{title}_{result_type}_template.csv"
#         response = HttpResponse(output.getvalue(), content_type='text/csv')
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
#         return response


import re   # noqa: E402  (shown here for completeness; put it with the other imports)

MAX_UPLOAD_BYTES = 1_000_000     # 1 MB is ~20k rows; a class is hundreds
MAX_IMPORT_ROWS = 2000
PREVIEW_ROWS = 200               # rows echoed back to the preview list
TITLE_MAX = 124                  # Result.title max_length


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────
class CsvImportError(ValueError):
    """A user-facing problem with the uploaded file (shown verbatim)."""


def _safe_filename(s):
    """Header-injection-proof filename fragment (no quotes / newlines / paths)."""
    return re.sub(r'[^A-Za-z0-9._-]+', '_', s or '').strip('_') or 'results'


def _csv_safe(v):
    """Neutralise spreadsheet formula injection (=, +, -, @ at cell start)."""
    s = '' if v is None else str(v)
    return "'" + s if s[:1] in ('=', '+', '-', '@') else s


def _validate_assessment(title, result_type):
    """-> (clean_title, error_message | None)"""
    title = (title or '').strip()
    if not title:
        return title, 'Please enter an assessment title.'
    if len(title) > TITLE_MAX:
        return title, f'Title is too long (max {TITLE_MAX} characters).'
    valid_types = [t[0] for t in RESULT_TYPE_CHOICES]
    if result_type not in valid_types:
        return title, f'Invalid type. Choose from {valid_types}.'
    return title, None


def _read_csv_upload(upload):
    """
    Uploaded file -> (header_cells, [(line_number, row_cells), ...]).
    Handles a UTF-8 BOM (Excel), quoted fields containing commas, and
    comma / semicolon / tab delimiters.
    """
    if upload is None:
        raise CsvImportError('Choose a CSV file to import.')
    if not upload.name.lower().endswith('.csv'):
        raise CsvImportError('Please upload a .csv file.')
    if upload.size > MAX_UPLOAD_BYTES:
        raise CsvImportError('That file is too large (max 1 MB).')

    raw = upload.read()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        # old Excel "CSV (comma delimited)"
        text = raw.decode('latin-1')

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=',;\t')
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    lines = []
    for row in reader:
        if any(c.strip() for c in row):
            lines.append((reader.line_num, row))

    if len(lines) < 2:
        raise CsvImportError(
            'The CSV needs a header row and at least one data row.')

    header = lines[0][1]
    data = lines[1:]
    if len(data) > MAX_IMPORT_ROWS:
        raise CsvImportError(
            f'Too many rows ({len(data)}). The limit is {MAX_IMPORT_ROWS} per import.')
    return header, data


def _find_columns(header):
    """-> (id_index, score_index, id_header, score_header). Column order is free."""
    cells = [c.strip().lower() for c in header]

    id_idx = next((i for i, c in enumerate(cells)
                   if 'reg' in c or 'admission' in c), None)
    if id_idx is None:
        id_idx = next((i for i, c in enumerate(cells)
                       if 'id' in re.split(r'[\s_\-]+', c)), None)
    score_idx = next((i for i, c in enumerate(cells)
                      if any(k in c for k in ('score', 'mark', 'point'))), None)

    if id_idx is None or score_idx is None:
        raise CsvImportError(
            'The header row needs a student ID column (e.g. "Student ID" or '
            '"Reg No") and a score column (e.g. "Score" or "Mark").')
    return id_idx, score_idx, header[id_idx].strip(), header[score_idx].strip()


def _cell(row, idx):
    return row[idx].strip() if idx < len(row) else ''


def _evaluate_import(curriculum, title, result_type, upload):
    """
    Parse + validate every row against the live roster. Pure read - nothing
    is written. Returns (items, (id_header, score_header)).

    item['status']: new | update | same | skipped | error
    """
    header, lines = _read_csv_upload(upload)
    id_idx, score_idx, id_header, score_header = _find_columns(header)

    enrollments = list(
        Enrollment.objects
        .filter(curriculum=curriculum, status='approved')
        .select_related('student__user')
    )
    by_reg = {e.student.registration_number.lower(): e for e in enrollments}
    existing = {
        str(r.enrollment_id): r.score
        for r in Result.objects.filter(
            enrollment_id__in=[e.record_id for e in enrollments],
            title=title, type=result_type)
    }

    seen = set()
    items = []
    for line_no, row in lines:
        reg = _cell(row, id_idx)
        raw = _cell(row, score_idx)
        item = {
            'line': line_no, 'registration_no': reg, 'name': '',
            'score': raw, 'score_value': None, 'status': 'error',
            'reason': '', 'current': None, 'enrollment': None,
        }
        items.append(item)

        if not reg:
            item['reason'] = 'Missing student ID'
            continue
        enrollment = by_reg.get(reg.lower())
        if enrollment is None:
            item['reason'] = 'Not enrolled in this course'
            continue

        item['name'] = enrollment.student.user.full_name
        item['enrollment'] = enrollment

        if reg.lower() in seen:
            item['reason'] = 'Duplicate row for this student'
            continue
        seen.add(reg.lower())

        if enrollment.graded_at is not None:
            item['reason'] = 'Already graded (locked)'
            continue
        if raw == '':
            item['status'] = 'skipped'
            item['reason'] = 'Blank score'
            continue

        try:
            score = Decimal(raw)
        except InvalidOperation:
            item['reason'] = 'Not a number'
            continue
        if not score.is_finite():
            item['reason'] = 'Not a number'
            continue
        if not (Decimal('0') <= score <= Decimal('100')):
            item['reason'] = 'Must be between 0 and 100'
            continue

        score = score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        item['score'] = str(score)
        item['score_value'] = score

        current = existing.get(str(enrollment.record_id))
        if current is None:
            item['status'] = 'new'
        elif current == score:
            item['status'] = 'same'
            item['current'] = str(current)
        else:
            item['status'] = 'update'
            item['current'] = str(current)

    return items, (id_header, score_header)


def _import_summary(items):
    def count(s): return sum(1 for i in items if i['status'] == s)   # noqa: E731
    return {
        'total':   len(items),
        'new':     count('new'),
        'update':  count('update'),
        'same':    count('same'),
        'skipped': count('skipped'),
        'errors':  count('error'),
    }


def _item_json(i):
    return {k: i[k] for k in
            ('line', 'registration_no', 'name', 'score', 'status', 'reason', 'current')}


# ─────────────────────────────────────────────────────────────────────────────
# AJAX - IMPORT scores from CSV (server-side parse, preview, commit)
# ─────────────────────────────────────────────────────────────────────────────
class ImportScoresAjaxView(RoleRequiredMixin, View):
    """
    POST /staff/lecturer/results/import-scores/      (multipart/form-data)
        curriculum_id, title, type, mode=preview|commit, file

    preview -> { summary, rows (<=200), truncated, columns }       (no writes)
    commit  -> { saved, skipped, summary, assessments }            (one transaction)

    Rules enforced HERE, never in the browser: file type/size/row limits,
    column detection, every id must be an approved student of THIS curriculum,
    0-100 scores (stored to 2dp), duplicates rejected, graded students and
    locked curricula refused. Blank scores are skipped (they never delete).a
    A title that doesn't exist yet simply creates the assessment.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        mode = request.POST.get('mode', 'preview')
        if mode not in ('preview', 'commit'):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        title, err = _validate_assessment(
            request.POST.get('title'), request.POST.get('type', ''))
        if err:
            return JsonResponse({'error': err}, status=400)
        result_type = request.POST['type']

        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=request.POST.get('curriculum_id'), professor=lecturer)
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({'error': 'Not found'}, status=404)

        locked = _locked_response(curriculum)
        if locked:
            return locked

        try:
            items, (id_header, score_header) = _evaluate_import(
                curriculum, title, result_type, request.FILES.get('file'))
        except CsvImportError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        summary = _import_summary(items)

        if mode == 'preview':
            # Problems first, so they are never hidden by the row cap.
            order = {'error': 0, 'skipped': 1,
                     'update': 2, 'new': 3, 'same': 4}
            shown = sorted(items, key=lambda i: (
                order[i['status']], i['line']))
            return JsonResponse({
                'mode':      'preview',
                'summary':   summary,
                'rows':      [_item_json(i) for i in shown[:PREVIEW_ROWS]],
                'truncated': len(shown) > PREVIEW_ROWS,
                'columns':   {'id': id_header, 'score': score_header},
            })

        # ── commit ───────────────────────────────────────────────────────
        todo = [i for i in items if i['status'] in ('new', 'update')]
        if not todo:
            return JsonResponse(
                {'error': 'Nothing to import - no row has a valid new or changed score.'},
                status=400)

        with transaction.atomic():
            for i in todo:
                Result.objects.update_or_create(
                    enrollment=i['enrollment'], title=title, type=result_type,
                    defaults={'score': i['score_value'],
                              'entered_by': request.user},
                )

        return JsonResponse({
            'mode':        'commit',
            'saved':       len(todo),
            'skipped':     len(items) - len(todo),
            'summary':     summary,
            'assessments': _build_assessment_list(curriculum),
        })


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT template (server-built, read-only - stays available after locking)
# ─────────────────────────────────────────────────────────────────────────────
class ExportTemplateView(RoleRequiredMixin, View):
    """
    GET /staff/lecturer/results/export-template/?curriculum=&title=&type=

    Roster CSV pre-filled with any scores already entered for (title, type).
    Works for an assessment that doesn't exist yet (Score column blank), which
    is exactly what the Import modal's "Download template" link needs.
    Columns: Student ID, Name, Class, Score - and the import accepts the file
    back as-is.
    """
    required_role = 'lecturer'

    def get(self, request):
        lecturer = self.get_profile()
        title = (request.GET.get('title') or 'Results').strip()[:TITLE_MAX]
        result_type = request.GET.get('type', 'C')
        if result_type not in [t[0] for t in RESULT_TYPE_CHOICES]:
            result_type = 'C'

        try:
            curriculum = Curriculum.objects.select_related('course').get(
                record_id=request.GET.get('curriculum'),
                professor=lecturer
            )
        except (Curriculum.DoesNotExist, ValueError, ValidationError):
            return HttpResponse('Not found', status=404)

        enrollments = list(
            Enrollment.objects
            .filter(curriculum=curriculum, status='approved')
            .select_related(
                'student__user',
                'student__class_entered'
            )
            .order_by('student__registration_number')
        )

        scores = dict(
            Result.objects
            .filter(
                enrollment_id__in=[e.record_id for e in enrollments],
                title=title,
                type=result_type
            )
            .values_list('enrollment_id', 'score')
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = '_'.join(_safe_filename(p) for p in (
            curriculum.course.course_code, title, result_type, 'template')) + '.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')                   # BOM so Excel reads UTF-8

        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Name', 'Class', 'Score'])
        for e in enrollments:
            s = scores.get(e.record_id)
            writer.writerow([
                _csv_safe(e.student.registration_number),
                _csv_safe(e.student.user.full_name),
                _csv_safe(
                    e.student.class_entered.class_name
                    if e.student.class_entered else ''
                ),
                '' if s is None else s,
            ])
        return response
