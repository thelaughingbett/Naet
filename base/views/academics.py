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


import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import ValidationError, PermissionDenied
from decouple import config

from django.http import JsonResponse
from django.shortcuts import (
    render,
)
from django.views import View
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.db import transaction

from base.models import (
    Curriculum,
    Session,
    Enrollment,
    Result,
    Syllabus,
    Student,
    Complaint,
    ComplaintDocument,
    AcademicRequisition,
    RequisitionDocument
)
from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)


class CurriculumView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/curriculum/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        active_session = self.get_active_session()

        syllabus_entries = Syllabus.objects.none()
        years = []
        total_credits = 0

        if student:
            programme = student.class_entered.programme

            # Full programme roadmap — every course a student in this
            # programme will ever take, not just what's been scheduled
            # into a Curriculum slot for their specific class/session.
            # Excludes Retired/Proposed/Under Review — only real,
            # currently-teachable entries should show on the roadmap.
            syllabus_entries = list(
                Syllabus.objects.filter(
                    programme=programme,
                    state__in=Syllabus.SCHEDULABLE_STATES,
                ).select_related('course').order_by('offered', 'course__course_code')
            )

            total_credits = sum(e.course.credits for e in syllabus_entries)

            duration_years = programme.duration_years or 1
            years = list(range(1, duration_years + 1))

            # Attach "currently scheduled" info only for entries actually
            # being taught to THIS student's class in the active session —
            # a future year's units won't have this yet, which is expected.
            if active_session:
                # Curriculum has no direct `syllabus` field anymore —
                # `course` is direct, and `classes` (through CurriculumClass)
                # is how we know this student's class is actually attached
                # to that slot. `class_links__syllabus__in=...` narrows it
                # to the specific syllabus-approved link, matching the old
                # per-syllabus semantics. Since Syllabus is unique per
                # (programme, course) and syllabus_entries is already
                # scoped to this student's programme, keying the lookup
                # dict by course_id is unambiguous.
                curricula = Curriculum.objects.filter(
                    classes=student.class_entered,
                    session=active_session,
                    class_links__syllabus__in=syllabus_entries,
                ).select_related('course').prefetch_related('professor__user').distinct()

                curriculum_by_course_id = {
                    c.course_id: c for c in curricula
                }

                for entry in syllabus_entries:
                    entry.current_curriculum = curriculum_by_course_id.get(
                        entry.course_id)
            else:
                for entry in syllabus_entries:
                    entry.current_curriculum = None

        context = {
            'syllabus_entries': syllabus_entries,
            'years': years,
            'total_credits': total_credits,
            'student': student,
            'session': active_session,
        }

        return render(request, 'base/academics/curriculum.html', context)


class UnitRegistrationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/units/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")
    min_credits = config("MIN_ELECTIVE_CREDITS", default=2, cast=int)
    max_credits = config("MAX_ELECTIVE_CREDITS", default=21, cast=int)

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled = []
        active_curriculum_ids = []
        available = Curriculum.objects.none()
        # Was previously undefined whenever `student` or `session` was
        # falsy — the context dict below always references it, which
        # would raise UnboundLocalError on that path. Initialize it
        # unconditionally.
        results_map = {}

        if student and session:
            enrolled_qs = Enrollment.objects.filter(
                student=student,
                curriculum__session=session,
            ).exclude(
                status='dropped'
            ).select_related(
                'curriculum__course'
            ).order_by('curriculum__course__course_code')

            active_curriculum_ids = list(
                enrolled_qs.values_list('curriculum_id', flat=True)
            )

            enrolled = list(enrolled_qs)

            # Published results for every enrolled row, fetched in one
            # query rather than N+1 through the `.results` property.
            enrollment_ids = [e.record_id for e in enrolled]
            published_results = Result.objects.filter(
                enrollment_id__in=enrollment_ids,
                state='published',
            ).order_by('type')

            for r in published_results:
                results_map.setdefault(str(r.enrollment_id), []).append({
                    'type': r.get_type_display(),
                    'title': r.title,
                    'score': float(r.score),
                })

            for e in enrolled:
                e.published_results_list = results_map.get(
                    str(e.record_id), [])

            # `Tclass=`/`syllabus__course__course_type=` no longer exist
            # on Curriculum. `classes=student.class_entered` requires a
            # CurriculumClass link already exists for this student's
            # class — i.e. this elective has actually been scheduled for
            # their class, matching the old per-class Curriculum row
            # semantics as closely as the new shared-slot schema allows.
            available = Curriculum.objects.filter(
                classes=student.class_entered,
                session=session,
                course__course_type='E',
            ).exclude(
                record_id__in=active_curriculum_ids
            ).select_related('course').distinct()

        context = {
            'available': available,
            'enrolled': enrolled,
            'results_by_enrollment': results_map,
            'student': student,
            'session': session,
            'min_credits': self.min_credits,
            'max_credits': self.max_credits,
        }
        return render(request, 'base/academics/unit_registration.html', context)

    def post(self, request):
        """
        Enroll in one or more selected elective units, pending department
        approval. Uses get_or_create + manual reset on the Enrollment
        model directly rather than the M2M `.add()` convenience — a
        previously DROPPED unit already has an Enrollment row for
        (student, curriculum), and unique_together on that pair means a
        second insert isn't possible. Re-registering has to reset the
        existing row instead of creating a new one.
        """
        student = self.get_student(request)
        session = self.get_active_session()
        curriculum_ids = request.POST.getlist('curriculum_ids')

        if not student or not session or not curriculum_ids:
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        active_curriculum_ids = Enrollment.objects.filter(
            student=student,
            curriculum__session=session,
        ).exclude(status='dropped').values_list('curriculum_id', flat=True)

        curricula = Curriculum.objects.filter(
            record_id__in=curriculum_ids,
            classes=student.class_entered,
            session=session,
            course__course_type='E',
        ).exclude(
            record_id__in=active_curriculum_ids
        ).select_related('course').distinct()

        if not curricula.exists():
            return JsonResponse({'success': False, 'message': 'No matching units found.'}, status=404)

        total_credits = sum(c.course.credits for c in curricula)

        if total_credits < self.min_credits:
            return JsonResponse({
                'success': False,
                'message': f"Minimum {self.min_credits} credits required — you selected {total_credits}.",
            }, status=400)

        if total_credits > self.max_credits:
            return JsonResponse({
                'success': False,
                'message': f"Maximum {self.max_credits} credits allowed — you selected {total_credits}.",
            }, status=400)

        with transaction.atomic():
            for curriculum in curricula:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    curriculum=curriculum,
                    defaults={'status': 'pending', 'approval_method': None},
                )
                if not created and enrollment.status == 'dropped':
                    enrollment.status = 'pending'
                    enrollment.approval_method = None
                    enrollment.approved_by = None
                    enrollment.approved_at = None
                    enrollment.save()

        return JsonResponse({
            'success': True,
            'message': f"{curricula.count()} unit(s) submitted for approval.",
        })


class DropElectiveUnitView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """Student self-service drop — electives only, pre-grading only."""

    def post(self, request):
        student = self.get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'No student profile.'}, status=403)

        enrollment_id = request.POST.get('enrollment_id')
        enrollment = Enrollment.objects.filter(
            record_id=enrollment_id,
            student=student,
        ).select_related('curriculum__course').first()

        if not enrollment:
            return JsonResponse({'success': False, 'message': 'Enrollment not found.'}, status=404)

        if enrollment.curriculum.course.course_type != 'E':
            return JsonResponse({
                'success': False,
                'message': 'Only elective units can be dropped here.',
            }, status=400)

        if enrollment.status == 'dropped':
            return JsonResponse({'success': False, 'message': 'This unit is already dropped.'}, status=400)

        try:
            enrollment.drop()
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': ' '.join(e.messages)}, status=400)

        return JsonResponse({
            'success': True,
            'message': f"{enrollment.curriculum.course.course_code} dropped.",
        })


class ResultsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/results/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        from base.models import Enrollment, Result
        student = self.get_student(request)
        active_session = self.get_active_session()

        enrollment_rows = []
        sessions = Session.objects.none()

        if student:
            target_class = student.class_entered

            # `curricula__Tclass` doesn't exist — `curricula` is the
            # related_name on Curriculum.session, and the class link is
            # now via `classes` (through CurriculumClass).
            earliest_session = Session.objects.filter(
                curricula__classes=target_class
            ).order_by('start_date').first()

            if earliest_session:
                sessions = Session.objects.filter(
                    start_date__gte=earliest_session.start_date
                ).order_by('start_date')

            # Every non-dropped/non-rejected enrollment — includes units
            # currently being taken (no results published yet) as well as
            # past graded ones, so the table always reflects the full
            # course load, not just what's already been marked.
            enrollments = Enrollment.objects.filter(
                student=student,
            ).exclude(
                status__in=['dropped', 'rejected']
            ).select_related(
                'curriculum__course',
                'curriculum__session',
            ).order_by('-curriculum__session__start_date')

            enrollment_ids = [e.record_id for e in enrollments]

            open_challenge_enrollment_ids = set(
                Complaint.objects.filter(
                    challenged_enrollment_id__in=enrollment_ids,
                    category='Results',
                    result_action='challenge',
                ).exclude(
                    status='Resolved'
                ).values_list('challenged_enrollment_id', flat=True)
            )

            # Only PUBLISHED CAT/Exam results — draft/submitted/disputed
            # results shouldn't display as a real score, and per the
            # requirement here, shouldn't count toward GPA either.
            published = Result.objects.filter(
                enrollment_id__in=enrollment_ids,
                type__in=['C', 'E'],
                state='published',
            ).order_by('record_id')

            scores_by_enrollment = {}
            for r in published:
                bucket = scores_by_enrollment.setdefault(
                    str(r.enrollment_id), {})
                # last published wins if more than one
                bucket[r.type] = float(r.score)

            for enr in enrollments:
                course = enr.curriculum.course
                bucket = scores_by_enrollment.get(str(enr.record_id), {})
                has_published = bool(bucket)

                enrollment_rows.append({
                    'session': str(enr.curriculum.session),
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'cat': bucket.get('C', 0),
                    'exam': bucket.get('E', 0),
                    'has_published': has_published,
                    'has_open_challenge': enr.record_id in open_challenge_enrollment_ids,
                })

        context = {
            'enrollment_rows': enrollment_rows,
            'student': student,
            'session': active_session,
            'sessions': sessions,
        }
        return render(request, 'base/academics/results.html', context)


# ── shared helpers ───────────────────────────────────────────────────────────

def _resolve_enrollment(student, course_code, session_str):
    """
    Scoped to this student's own, non-dropped enrollments. Returns None
    rather than raising — callers turn that into a clean 404-style
    message instead of a validation error.
    """
    enr_qs = Enrollment.objects.filter(
        student=student,
        curriculum__course__course_code=course_code,
    ).exclude(
        status__in=['dropped', 'rejected']
    ).select_related('curriculum__course', 'curriculum__session')

    if session_str:
        return next(
            (e for e in enr_qs if str(e.curriculum.session) == session_str), None
        )
    return enr_qs.order_by('-curriculum__session__start_date').first()


def _attach_documents(request, doc_model, **base_kwargs):
    """
    doc_model is ComplaintDocument or RequisitionDocument — both share
    the same shape (file + clean()'s extension check), just different
    parent FK names, which base_kwargs supplies.
    """
    for f in request.FILES.getlist("documents"):
        doc = doc_model(file=f, **base_kwargs)
        doc.full_clean()  # re-enforces the allowed-extension list server-side
        doc.save()


def _flatten_errors(e):
    messages_out = []
    for field, errs in getattr(e, "message_dict", {"__all__": e.messages}).items():
        messages_out.extend(errs)
    return " ".join(messages_out)


# ── grade challenges (Complaint) ─────────────────────────────────────────────

@login_required
@require_GET
def result_challenge_history(request):
    """JSON history of grade-challenge complaints for the signed-in student."""
    student = Student.objects.filter(user=request.user).first()
    if not student:
        return JsonResponse({"items": []})

    qs = Complaint.objects.filter(
        student=student,
        category='Results',
        result_action='challenge',
    ).select_related(
        'challenged_enrollment__curriculum__course',
        'challenged_enrollment__curriculum__session',
    ).prefetch_related(
        'documents', 'escalation_history'
    ).order_by('-date_opened')

    course_code = request.GET.get('course_code')
    if course_code:
        qs = qs.filter(
            challenged_enrollment__curriculum__course__course_code=course_code
        )

    items = []
    for c in qs:
        enr = c.challenged_enrollment
        course = enr.curriculum.course if enr else None
        items.append({
            "id":            str(c.record_id),
            "status":        c.status,
            "status_label":  c.get_status_display(),
            "level_label":   c.get_current_level_display() if c.current_level else "—",
            "date_opened":   c.date_opened.strftime("%d %b %Y, %H:%M"),
            "sla_due_at":    c.sla_due_at.strftime("%d %b %Y, %H:%M") if c.sla_due_at else None,
            "date_resolved": c.date_resolved.strftime("%d %b %Y, %H:%M") if c.date_resolved else None,
            "resolution":    c.resolution_remarks or "",
            "description":   c.description,
            "course_code":   course.course_code if course else "—",
            "course_name":   course.course_name if course else "—",
            "session":       str(enr.curriculum.session) if enr else "—",
            # Frozen at filing — deliberately not the live marks, which
            # may since have been corrected in response to this challenge.
            "snapshot": {
                "cat":   float(c.snapshot_cat) if c.snapshot_cat is not None else None,
                "exam":  float(c.snapshot_exam) if c.snapshot_exam is not None else None,
                "total": float(c.snapshot_total) if c.snapshot_total is not None else None,
                "grade": c.snapshot_grade or "—",
            },
            "documents": [
                {"name": d.original_name, "url": d.file.url} for d in c.documents.all()
            ],
            "escalations": [
                {
                    "from":      e.escalated_from_level,
                    "to":        e.escalated_to_level,
                    "automatic": e.is_automatic,
                    "reason":    e.reason_for_escalation,
                    "date":      e.date_escalated.strftime("%d %b %Y, %H:%M"),
                }
                for e in c.escalation_history.all()
            ],
        })

    return JsonResponse({"items": items})


@login_required
@require_POST
def submit_result_challenge(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        raise PermissionDenied("Only students can file result challenges.")

    course_code = (request.POST.get("course_code") or "").strip()
    session_str = (request.POST.get("session") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    if not reason:
        return JsonResponse(
            {"success": False, "message": "Please give a reason for this request."},
            status=400,
        )

    enrollment = _resolve_enrollment(student, course_code, session_str)
    if not enrollment:
        return JsonResponse(
            {"success": False, "message": "You aren't registered for that unit."},
            status=404,
        )

    existing = Complaint.objects.filter(
        student=student, category='Results', result_action='challenge',
        challenged_enrollment=enrollment,
    ).exclude(status='Resolved').first()
    if existing:
        return JsonResponse(
            {"success": False, "message": "You already have an open challenge for this unit."},
            status=409,
        )

    course = enrollment.curriculum.course
    complaint = Complaint(
        student=student,
        category='Results',
        result_action='challenge',
        challenged_enrollment=enrollment,
        subject=f"Grade challenge — {course.course_code} {course.course_name}"[
            :255],
        description=reason,
        priority='Medium',
    )

    try:
        with transaction.atomic():
            complaint.full_clean()
            complaint.save()
            _attach_documents(
                request, ComplaintDocument,
                complaint=complaint,
                uploaded_by_role='student',
                uploaded_by_user=request.user,
            )
    except ValidationError as e:
        return JsonResponse({"success": False, "message": _flatten_errors(e)}, status=400)

    return JsonResponse({
        "success": True,
        "message": "Your challenge has been logged and routed for review.",
        "level": complaint.get_current_level_display(),
    })


# ── academic requisitions (resit / supplementary / missing marks / special exam) ─

@login_required
@require_GET
def requisition_history(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        return JsonResponse({"items": []})

    qs = AcademicRequisition.objects.filter(
        student=student,
    ).select_related(
        'enrollment__curriculum__course',
        'enrollment__curriculum__session',
        'scheduled_venue',
        'hod_reviewed_by', 'approved_by',
    ).prefetch_related('documents').order_by('-requested_at')

    course_code = request.GET.get('course_code')
    if course_code:
        qs = qs.filter(enrollment__curriculum__course__course_code=course_code)

    items = []
    for r in qs:
        course = r.enrollment.curriculum.course
        items.append({
            "id":            str(r.record_id),
            "type":          r.type,
            "type_label":    r.get_type_display(),
            "status":        r.status,
            "status_label":  r.get_status_display(),
            "date_opened":   r.requested_at.strftime("%d %b %Y, %H:%M"),
            "reason":        r.reason,
            "course_code":   course.course_code,
            "course_name":   course.course_name,
            "session":       str(r.enrollment.curriculum.session),
            "hod": {
                "by":      r.hod_reviewed_by.half_name if r.hod_reviewed_by else None,
                "at":      r.hod_reviewed_at.strftime("%d %b %Y, %H:%M") if r.hod_reviewed_at else None,
                "remarks": r.hod_remarks or "",
            },
            "registrar": {
                "by":      r.approved_by.half_name if r.approved_by else None,
                "at":      r.approved_at.strftime("%d %b %Y, %H:%M") if r.approved_at else None,
                "remarks": r.registrar_remarks or "",
            },
            "fee": {
                "required": r.fee_required,
                "amount":   float(r.fee_amount) if r.fee_amount is not None else None,
                "paid":     r.fee_paid,
                "paid_at":  r.fee_paid_at.strftime("%d %b %Y, %H:%M") if r.fee_paid_at else None,
            },
            "schedule": {
                "date":      r.scheduled_date.strftime("%d %b %Y") if r.scheduled_date else None,
                "time_slot": r.scheduled_time_slot,
                "venue":     r.scheduled_venue.venue_name if r.scheduled_venue else None,
            },
            "completed_at": r.completed_at.strftime("%d %b %Y, %H:%M") if r.completed_at else None,
            "documents": [
                {"name": d.original_name, "url": d.file.url} for d in r.documents.all()
            ],
        })

    return JsonResponse({"items": items})


@login_required
@require_POST
def submit_requisition(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        raise PermissionDenied("Only students can file academic requisitions.")

    course_code = (request.POST.get("course_code") or "").strip()
    session_str = (request.POST.get("session") or "").strip()
    req_type = (request.POST.get("type") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    valid_types = {c[0]
                   for c in AcademicRequisition._meta.get_field('type').choices}
    if req_type not in valid_types:
        return JsonResponse({"success": False, "message": "Unknown request type."}, status=400)
    if not reason:
        return JsonResponse(
            {"success": False, "message": "Please give a reason for this request."},
            status=400,
        )

    enrollment = _resolve_enrollment(student, course_code, session_str)
    if not enrollment:
        return JsonResponse(
            {"success": False, "message": "You aren't registered for that unit."},
            status=404,
        )

    requisition = AcademicRequisition(
        student=student,
        enrollment=enrollment,
        type=req_type,
        reason=reason,
    )

    try:
        with transaction.atomic():
            requisition.full_clean()  # also enforces the one-open-request-per-type rule
            requisition.save()
            _attach_documents(
                request, RequisitionDocument,
                requisition=requisition,
                uploaded_by_user=request.user,
            )
    except ValidationError as e:
        return JsonResponse({"success": False, "message": _flatten_errors(e)}, status=400)

    return JsonResponse({
        "success": True,
        "message": "Your request has been submitted for HOD review.",
        "status": requisition.get_status_display(),
    })
