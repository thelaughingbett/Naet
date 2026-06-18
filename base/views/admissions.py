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

from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
import datetime
import types

from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError

from django.shortcuts import render, redirect
from django.contrib import messages


from decouple import config

from django.shortcuts import (
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,

)
from base.forms import ReportingForm
from base.models import (
    Reporting,
    Hostel,
    Room,
    HostelAllocation,
    Session,
    ExamCard,
    ExamClash,
    ExamSession,
    HostelListing,
    Deferment,
    DefermentDocument
)
from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)


class ReportingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """
    Handles the student semester check-in / reporting registration process.

    This view manages both the rendering of the reporting status portal (GET)
    and the creation of a session reporting log upon successful form submission (POST).

    Access Control & Context Inheritance:
        - LoginRequiredMixin: Restricts access to authenticated portal accounts.
        - StudentProfileRequiredMixin: Ensures the logged-in user possesses an active Student profile.
        - StudentContextMixin: Provides helper access methods (`get_student`, `get_active_session`).

    Template:
        - `base/admissions/reporting.html`
    """

    login_url = config("LOGIN_URL") + '?next=admissions/reporting/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        """
            Renders the reporting portal layout.

            Evaluates check-in records to conditionally toggle dashboard action
            panels inside the template.
        """
        student = self.get_student(request)
        session = self.get_active_session()

        already_reported = None
        if student and session:
            already_reported = Reporting.objects.filter(
                student=student,
                session=session
            ).first()

        context = {
            'already_reported': already_reported,
            'session': session,
            'student': student,
        }
        return render(request, 'base/admissions/reporting.html', context)

    def post(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('No active session', status=400)

        if Reporting.objects.filter(student=student, session=session).exists():
            return HttpResponse('Already reported for this session', status=400)

        form = ReportingForm(request.POST)
        if form.is_valid():
            reporting = form.save(commit=False)
            reporting.student = student
            reporting.session = session
            reporting.reported_at = datetime.datetime.now()
            reporting.reported_via = Reporting.REPORTED_VIA_CHOICES[0][0]
            reporting.save()

            from base.modules.notifications.service import NotificationService
            NotificationService.send(
                user=types.SimpleNamespace(
                    email=student.user.email,
                    phone_number=student.telephone_no
                ),
                template_key='reporting_confirmed',
                channels=['sms', 'email'],
                context={
                    'student_name': student.user.half_name,
                    'session': session,
                    # BUG 🪳 sends  wrong reverse  url
                    # TODO 📋: FIX BUG
                    'portal_url': reverse('base-index')
                }
            )
            # ← back to self, GET will pick up already_reported
            return redirect('base-reporting')

        student_obj = self.get_student(request)
        context = {
            'form': form,
            'session': session,
            'student': student_obj,
            'already_reported': None,
        }
        return render(request, 'base/admissions/reporting.html', context)


class DefermentView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View,
):
    login_url = config("LOGIN_URL") + '?next=admissions/defer/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        active_session = self.get_active_session()

        # All sessions available to defer into (active + future)
        available_sessions = Session.objects.filter(
            start_date__gte=active_session.start_date
        ).order_by('start_date') if active_session else Session.objects.none()

        # Current pending request if any
        pending = Deferment.objects.filter(
            student=student,
            request_status='pending'
        ).first() if student else None

        # Full history
        history = Deferment.objects.filter(
            student=student
        ).select_related(
            'session_deferred', 'session_returning', 'approved_by'
        ).prefetch_related(
            'documents'
        ).order_by('-created_at') if student else []

        return render(request, 'base/admissions/defer.html', {
            'student':            student,
            'active_session':     active_session,
            'available_sessions': available_sessions,
            'reason_choices':     Deferment.REASON_CHOICES,
            'pending':            pending,
            'history':            history,
        })

    def post(self, request):
        student = self.get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'Student not found.'}, status=404)

        session_id = request.POST.get('session_deferred')
        reason = request.POST.get('reason')
        reason_detail = request.POST.get('reason_detail', '').strip()
        files = request.FILES.getlist('documents')

        # Validate
        if not session_id or not reason:
            return JsonResponse({
                'success': False,
                'message': 'Session and reason are required.'
            }, status=400)

        session = Session.objects.filter(record_id=session_id).first()
        if not session:
            return JsonResponse({'success': False, 'message': 'Invalid session.'}, status=400)

        # Prevent duplicate pending request for same session
        if Deferment.objects.filter(student=student, session_deferred=session).exists():
            return JsonResponse({
                'success': False,
                'message': f'You already have a deferment request for {session}.'
            }, status=400)

        # Create deferment record
        deferment = Deferment.objects.create(
            student=student,
            session_deferred=session,
            reason=reason,
            reason_detail=reason_detail or None,
            request_status='pending',
            status='active',
        )

        # Attach documents
        for f in files:
            if f.size > 5 * 1024 * 1024:   # 5 MB cap
                deferment.delete()
                return JsonResponse({
                    'success': False,
                    'message': f'File "{f.name}" exceeds the 5 MB limit.'
                }, status=400)
            DefermentDocument.objects.create(
                deferment=deferment,
                file=f,
                original_name=f.name,
            )

        # Flag student as deferred
        student.deferred = True
        student.save()

        return JsonResponse({
            'success':    True,
            'message':    'Your deferment request has been submitted and is pending review.',
            'ref':        str(deferment.record_id)[:8].upper(),
            'session':    str(session),
            'reason':     deferment.get_reason_display(),
            'doc_count':  len(files),
        })


class HostelBookingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/hostel/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = Session.objects.filter(is_active=True).first()

        current_allocation = None
        if student and session:
            current_allocation = (
                HostelAllocation.objects
                .filter(student=student, session=session, is_active=True)
                .select_related('room__hostel')
                .first()
            )

        hostels = Hostel.objects.prefetch_related('rooms').all()
        if student:
            hostels = hostels.filter(
                Q(gender=student.user.gender) | Q(gender='mixed')
            )

        rooms_json = []
        for hostel in hostels:
            for room in hostel.rooms.all():
                rooms_json.append({
                    'id': room.record_id,
                    'hostel_id': hostel.record_id,
                    'hall': hostel.name,
                    'type': room.room_type,
                    'type_display': room.get_room_type_display(),
                    'room_number': room.room_number,
                    'capacity': room.capacity,
                    'price': room.price_per_semester,
                    'available': not room.is_full,
                    'available_beds': room.capacity - room.allocations.filter(is_active=True).count(),
                })

        context = {
            'student': student,
            'session': session,
            'current_allocation': current_allocation,
            'hostels': hostels,
            'room_types': Room.ROOM_TYPE_CHOICES,
            'rooms_json': rooms_json,
        }
        return render(request, 'base/admissions/hostel_booking.html', context)

    def post(self, request):
        student = self.get_student(request)
        room_id = request.POST.get('room')

        if not student or not room_id:
            return HttpResponse('Invalid request', status=400)

        session = Session.objects.filter(is_active=True).first()
        if not session:
            return HttpResponse('No active session', status=400)

        if HostelAllocation.objects.filter(
            student=student, session=session, is_active=True
        ).exists():
            return HttpResponse(
                'You already have a hostel allocation for this session', status=400
            )

        room = Room.objects.filter(pk=room_id).select_related('hostel').first()
        if not room:
            return HttpResponse('Room not found', status=404)

        allocation = HostelAllocation(
            student=student,
            room=room,
            session=session,
            move_in_date=request.POST.get('move_in_date') or None,
            notes=request.POST.get('special_requests', '').strip(),
        )

        try:
            allocation.full_clean()  # gender + capacity checks from clean()
        except ValidationError as e:
            return HttpResponse('; '.join(e.messages), status=400)

        allocation.save()

        student.stay = 'resident'
        student.save()

        return redirect('base-hostel-booking')


class ExamCardView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """
    Exam admit card view.

    Access is gated — a student must:
        1. Have a student profile
        2. Have a fee account for the active session
        3. Have cleared their fees (account.is_cleared)
        4. Have at least one approved enrollment this session

    Edge cases handled:
        - No active session
        - No fee structure for student's class
        - No fee account at all
        - Fee account exists but not cleared
        - No approved enrollments (nothing to examine)
        - Existing active card (reuse serial + QR)
        - Exam clashes detected

    GET  → render exam card or appropriate gate screen
    POST → regenerate serial number (new ExamCard, old one deactivated)
    """

    template_name = 'base/exam-card/exam_card.html'
    login_url = config("LOGIN_URL") + '?next=/admissions/exam-card/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def _get_fee_account(self, student, session):
        """
        Returns (account, error_key) where error_key is None on success.

        error_key values:
            'no_structure'  — no FeeStructure for student's class this session
            'no_account'    — FeeStructure exists but no StudentFeeAccount
            'not_cleared'   — account exists but balance > 0
        """
        from base.models import FeeStructure, StudentFeeAccount

        structure = FeeStructure.objects.filter(
            Tclass=student.class_entered,
            session=session
        ).first()

        if not structure:
            return None, 'no_structure'

        account = StudentFeeAccount.objects.filter(
            student=student,
            fee_structure=structure
        ).first()

        if not account:
            return None, 'no_account'

        if not account.is_cleared:
            return account, 'not_cleared'

        return account, None

    def _get_or_create_card(self, student, session):
        """
        Returns the active ExamCard for this student/session.
        Creates one if none exists.
        """
        card = ExamCard.objects.filter(
            student=student,
            session=session,
            is_active=True
        ).first()

        if not card:
            card = ExamCard.objects.create(
                student=student,
                session=session,
                serial_number=ExamCard.generate_serial(),
                is_active=True
            )

        return card

    def _get_exam_schedule(self, student, session):
        """
        Returns ExamSession queryset for approved enrollments
        in the active session, ordered by date + time slot.
        """
        enrolled_curriculum_ids = student.enrollment_records.filter(
            curriculum__session=session,
            status='approved'
        ).values_list('curriculum_id', flat=True)

        return ExamSession.objects.filter(
            curriculum_id__in=enrolled_curriculum_ids
        ).select_related(
            'curriculum__course',
            'curriculum__Tclass',
        ).prefetch_related(
            'venues__venue',
            'venues__invigilator__user',
        ).order_by('date', 'time_slot')

    def _get_clashes(self, student, session):
        return ExamClash.objects.filter(
            student=student,
            session_a__curriculum__session=session,
            resolved=False
        ).select_related(
            'session_a__curriculum__course',
            'session_b__curriculum__course',
        )

    def get(self, request):
        student = self.get_student(request)
        if not student:
            messages.error(request, "Student profile not found.")
            return redirect('base-dashboard')

        session = self.get_active_session()
        if not session:
            return render(request, self.template_name, {
                'gate': 'no_session',
                'student': student,
            })

        account, error = self._get_fee_account(student, session)

        if error == 'no_structure':
            return render(request, self.template_name, {
                'gate':    'no_structure',
                'student': student,
                'session': session,
            })

        if error == 'no_account':
            return render(request, self.template_name, {
                'gate':    'no_account',
                'student': student,
                'session': session,
            })

        if error == 'not_cleared':
            return render(request, self.template_name, {
                'gate':          'not_cleared',
                'student':       student,
                'session':       session,
                'account':       account,
                'balance':       account.balance,
                'days_remaining': account.days_remaining,
            })

        exam_schedule = self._get_exam_schedule(student, session)

        if not exam_schedule.exists():
            return render(request, self.template_name, {
                'gate':    'no_exams',
                'student': student,
                'session': session,
            })

        card = self._get_or_create_card(student, session)
        clashes = self._get_clashes(student, session)

        card.last_printed_at = timezone.now()
        card.save(update_fields=['last_printed_at'])

        return render(request, self.template_name, {
            'gate':          None,
            'student':       student,
            'session':       session,
            'account':       account,
            'card':          card,
            'exam_schedule': exam_schedule,
            'clashes':       clashes,
            'has_clashes':   clashes.exists(),
            'qr_payload':    card.qr_payload,
            'issued_at':     card.issued_at,
        })

    def post(self, request):
        student = self._get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'No student profile.'}, status=403)

        session = self._get_session()
        if not session:
            return JsonResponse({'success': False, 'message': 'No active session.'}, status=400)

        account, error = self._get_fee_account(student, session)
        if error:
            return JsonResponse({'success': False, 'message': 'Fee account not cleared.'}, status=403)

        # deactivate existing card
        ExamCard.objects.filter(
            student=student,
            session=session,
            is_active=True
        ).update(is_active=False)

        # issue new card with fresh serial
        new_serial = ExamCard.generate_serial()
        card = ExamCard.objects.create(
            student=student,
            session=session,
            serial_number=new_serial,
            is_active=True
        )

        return JsonResponse({
            'success':     True,
            'serial':      card.serial_number,
            'qr_payload':  card.qr_payload,
        })


class HostelGuideView(View):
    def get(self, request):
        hostels = HostelListing.objects.filter(is_published=True)
        return render(request, 'base/hostel-guide.html', {
            'hostels': hostels
        })
