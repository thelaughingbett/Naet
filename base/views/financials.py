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

from django.http import JsonResponse
from django.core.exceptions import ValidationError
from base.models import Payment
from django.views.decorators.cache import never_cache
from django.contrib import messages

from http import HTTPStatus
import logging

from decouple import config

from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.views.generic import (
    DetailView,
    ListView,
    DeleteView
)
from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.db import (
    DatabaseError,
    IntegrityError,
    transaction
)
from django.utils.http import url_has_allowed_host_and_scheme

from base.models import (
    Student,
    Session,
    FeeStructure,
    StudentFeeAccount,
    Payment
)
from base.forms import (
    PaymentForm
)
from base.modules.payments.registry import registry as payment_registry
from base.modules.payments.services import PaymentService

from .base import (
    StudentContextMixin,
    StudentProfileRequiredMixin
)


class FeeStatementView(LoginRequiredMixin, StudentProfileRequiredMixin, StudentContextMixin, View):
    login_url = config("LOGIN_URL") + '?next=financials/fees/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session_id = request.GET.get('session')

        if session_id:
            session = Session.objects.filter(record_id=session_id).first()
        else:
            session = self.get_active_session()

        fee_structure = None
        account = None

        if student and session:
            fee_structure = FeeStructure.objects.filter(
                Tclass=student.class_entered,
                session=session
            ).first()

            if fee_structure:
                account = StudentFeeAccount.objects.select_related(
                    'fee_structure__session',
                    'fee_structure__Tclass',
                ).filter(
                    student=student,
                    fee_structure=fee_structure
                ).first()

        all_sessions = Session.objects.filter(
            fee_structures__Tclass=student.class_entered
        ).distinct().order_by('-academic_year', '-semester') if student else []

        return render(request, 'base/financials/fee_statement.html', {
            'fee_structure':       fee_structure,
            'account':             account,
            'all_sessions':        all_sessions,
            # Always the actual session record_id so the dropdown stays selected
            'selected_session_id': str(session.record_id) if session else '',
            'student':             student,
            'session':             session,
        })


class PaymentView(LoginRequiredMixin, StudentProfileRequiredMixin, View):
    login_url = config('LOGIN_URL') + '?next=financials/fees/pay/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def _get_context(self, student, session):
        """Shared between get and post — fetch structure and account."""
        structure = FeeStructure.objects.filter(
            Tclass=student.class_entered,
            session=session
        ).first()

        account = StudentFeeAccount.objects.filter(
            student=student,
            fee_structure__session=session
        ).order_by('-created_at').first() if structure else None

        accounts = StudentFeeAccount.objects.filter(student=student)

        return structure, account

    def post(self, request):
        session = Session.objects.filter(is_active=True).first()
        if not session:
            return JsonResponse({"success": False, "message": "No active session."}, status=400)

        student = request.user.student_profile
        structure, account = self._get_context(student, session)

        if not account:
            return JsonResponse({"success": False, "message": "No fee account found."}, status=404)

        if account.is_cleared:
            return JsonResponse({"success": False, "message": "Your account is already cleared."}, status=400)

        form = PaymentForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"success": False, "errors": form.errors}, status=422)

        method = form.cleaned_data['method']
        backend = payment_registry.get(method)

        if not backend:
            return JsonResponse({"success": False, "message": f"Method '{method}' not supported."}, status=400)

        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    **form.cleaned_data,
                    account=account,
                    status='pending'
                )
                result = PaymentService.initiate(
                    payment, **request.POST.dict())

            if not result.success:
                return JsonResponse({"success": False, "message": result.message}, status=400)

            return JsonResponse({
                "success":      True,
                "flow":         backend.get_form_config().flow,
                "payment_id":   str(payment.record_id),
                "message":      result.message or "Payment initiated.",
                "redirect_url": result.redirect_url,
                "provider_ref": result.provider_ref,
            })

        except ValidationError as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

        except DatabaseError:
            return JsonResponse({"success": False, "message": "Database error. Please try again."}, status=500)


class PaymentConfigView(View):
    """
    GET /payments/config/
    Returns form configs for all registered backends.
    No auth needed — configs are not sensitive.
    """

    def get(self, request):
        configs = []
        for backend in payment_registry.all():
            config = backend.get_form_config()
            configs.append({
                "method":       config.method,
                "label":        config.label,
                "icon":         config.icon,
                "flow":         config.flow,
                "instructions": config.instructions,
                "fields": [
                    {
                        "name":        f.name,
                        "label":       f.label,
                        "type":        f.type,
                        "required":    f.required,
                        "placeholder": f.placeholder,
                        "help_text":   f.help_text,
                        "options":     f.options,
                    }
                    for f in config.fields
                ],
            })
        return JsonResponse({"methods": configs})


class PaymentStatusView(LoginRequiredMixin, View):
    """
    GET /payments/status/<payment_id>/
    Frontend polls this after stk_push to check if confirmed.
    """

    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment,
            record_id=payment_id,
            account__student=request.user.student_profile
        )
        return JsonResponse({
            "status":          payment.status,
            "transaction_ref": payment.transaction_ref,
            "amount":          str(payment.amount),
            "message":         payment.get_status_display(),
        })
