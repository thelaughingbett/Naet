# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

# adjust import path to match your layout
from base.models import StudentMedicalProfile
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from decouple import config

from base.forms import LoginForm
from base.forms.auth import (
    ChangePasswordform,
    EmergencyContactFormSet,
    StudentSettingsForm,
    UserSettingsForm,
    StudentMedicalProfileForm
)
from base.models import (
    IDCard,
    EmergencyContact,
    Enrollment,
    ItStaff,
    Lecturer,
    Student,
)
from .base import StudentContextMixin, StudentProfileRequiredMixin
from staffConsole.views.base import get_staff_dashboard_url


def _resolve_post_login_url(request, user) -> str:
    """
    Priority order:
      1. ?next= query param (only if it's a safe relative path — prevents
         open-redirect attacks by ignoring anything that looks like an
         absolute URL or starts with //).
      2. Role-based dashboard from get_staff_dashboard_url (staff users).
      3. base-index (students / fallback).
    """
    next_url = request.GET.get('next', '').strip()

    # Accept the next param only if it's a safe relative URL.
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return next_url

    # Staff → their role-specific dashboard.
    if user.is_staff:
        staff_url = get_staff_dashboard_url(user)
        if staff_url and staff_url != '/':
            return staff_url

    # Students and any unrecognised role → student portal landing page.
    # TODO : check for student profile and end this function with bad_request if role not defined
    return reverse('base-index')


class LoginView(View):

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_resolve_post_login_url(request, request.user))
        return render(request, 'base/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)

        if not form.is_valid():
            return render(request, 'base/login.html', {'form': form})

        input_login = form.cleaned_data['email'].strip()
        password = form.cleaned_data['password']

        # ── attempt 1: treat input as a real email ────────────────────────
        user = authenticate(
            request,
            username=input_login,
            password=password
        )

        # ── attempt 2: resolve reg-number / school-email / staff-number ──
        if user is None:
            resolved_email = _resolve_login_identifier(input_login)
            if resolved_email:
                user = authenticate(
                    request,
                    username=resolved_email,
                    password=password
                )

        if user is None:
            form.add_error(None, "Invalid credentials or password.")
            return render(request, 'base/login.html', {'form': form})

        # ── success ───────────────────────────────────────────────────────
        login(request, user)

        if form.cleaned_data.get('remember_me'):
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            request.session.set_expiry(0)                   # browser session

        return redirect(_resolve_post_login_url(request, user))


def _resolve_login_identifier(input_login: str) -> str | None:
    """
    Given a non-email identifier (registration number, school email, or staff
    number), return the canonical auth email for that user, or None.

    Kept as a module-level function so it can be unit-tested independently.
    """
    # Student: match by registration number or school email
    student_match = (
        Student.objects
        .filter(
            models.Q(registration_number__iexact=input_login) |
            models.Q(school_email__iexact=input_login)
        )
        .select_related('user')
        .first()
    )
    if student_match and getattr(student_match, 'user', None):
        return student_match.user.email

    # Staff: match by staff number across all staff models
    for staff_model in (Lecturer, ItStaff):
        match = (
            staff_model.objects
            # TODO : check email also
            .filter(staff_number__iexact=input_login)
            .select_related('user')
            .first()
        )
        if match and getattr(match, 'user', None):
            return match.user.email

    return None


# ─────────────────────────────────────────────────────────────────────────────

class LogoutView(View):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def post(self, request):
        logout(request)
        return redirect(reverse('base-login'))


# ─────────────────────────────────────────────────────────────────────────────

class SettingsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View,
):
    login_url = config('LOGIN_URL') + '?next=settings'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def _get_medical_profile(self, student):
        try:
            return student.medical_profile
        except StudentMedicalProfile.DoesNotExist:
            return StudentMedicalProfile(student=student)

    def _get_id_card(self, student):
        """
        Unlike medical_profile, this is never built unsaved — an ID card
        is issued by the registrar, not self-served, so there's nothing
        for a student to fill in if one doesn't exist yet. Returns None
        rather than an unsaved instance.
        """
        try:
            return student.id_card
        except IDCard.DoesNotExist:
            return None

    def _build_tabs(self, request, post_data=None, files_data=None):
        user = request.user
        student = self.get_student(request)
        queryset = EmergencyContact.objects.filter(student=student)
        medical_profile = self._get_medical_profile(student)
        id_card = self._get_id_card(student)

        user_form = UserSettingsForm(post_data, files_data, instance=user)
        student_form = StudentSettingsForm(post_data, instance=student)
        emergency_formset = EmergencyContactFormSet(
            post_data, queryset=queryset, prefix='emergency'
        )
        medical_form = StudentMedicalProfileForm(
            post_data, instance=medical_profile)
        password_form = ChangePasswordform(post_data, user=user)

        tabs_config = [
            {
                'id':         'general',
                'title':      'General Info',
                'form':       user_form,
                'is_formset': False,
                'legend':     'General Profile Details',
                'has_errors': bool(user_form.errors),
            },
            {
                'id':         'personal',
                'title':      'Personal Info',
                'form':       student_form,
                'is_formset': False,
                'legend':     'Personal Settings & Identification',
                'has_errors': bool(student_form.errors),
            },
            {
                'id':         'emergency',
                'title':      'Emergency Contacts',
                'formset':    emergency_formset,
                'is_formset': True,
                'legend':     'Emergency Contact Info (Maximum 4)',
                'has_errors': any(emergency_formset.errors) or bool(emergency_formset.non_form_errors()),
            },
            {
                'id':         'medical',
                'title':      'Medical Profile',
                'form':       medical_form,
                'is_formset': False,
                'legend':     'Medical Profile & Consent',
                'has_errors': bool(medical_form.errors),
            },
            {
                'id':         'id_card',
                'title':      'Student ID',
                'is_formset': False,
                'is_readonly': True,
                'legend':     'Student Identification Card',
                'has_errors': False,
                'id_card':    id_card,
            },
            {
                'id':         'password',
                'title':      'Change Password',
                'form':       password_form,
                'is_formset': False,
                'legend':     'Change Password',
                'has_errors': bool(password_form.errors),
            },
        ]
        return {
            'tabs_config':       tabs_config,
            'student':           student,
            'user_form':         user_form,
            'student_form':      student_form,
            'emergency_formset': emergency_formset,
            'medical_form':      medical_form,
            'password_form':     password_form,
        }

    def _active_tab(self, built, password_submitted):
        """
        Re-render on the tab that actually has errors, instead of always
        snapping back to General and hiding what went wrong.
        """
        if built['user_form'].errors:
            return 'general'
        if built['student_form'].errors:
            return 'personal'
        if any(built['emergency_formset'].errors) or built['emergency_formset'].non_form_errors():
            return 'emergency'
        if built['medical_form'].errors:
            return 'medical'
        if password_submitted and built['password_form'].errors:
            return 'password'
        return 'general'

    def get(self, request):
        built = self._build_tabs(request)
        return render(request, 'base/settings.html', {
            'tabs_config':       built['tabs_config'],
            'emergency_formset': built['emergency_formset'],
            'active_tab':        'general',
        })

    def post(self, request):
        built = self._build_tabs(request, request.POST, request.FILES)
        user_form = built['user_form']
        student_form = built['student_form']
        emergency_formset = built['emergency_formset']
        medical_form = built['medical_form']
        password_form = built['password_form']
        student = self.get_student(request)
        # Every tab lives inside one <form> with a single Save Settings
        # button, so the password fields are always present in POST —
        # usually empty. Only require them to validate if the person
        # actually typed something into one of them.
        password_submitted = any(
            request.POST.get(f) for f in ('old_password', 'password', 'password_confirm')
        )

        forms_valid = (
            user_form.is_valid()
            and student_form.is_valid()
            and emergency_formset.is_valid()
            and medical_form.is_valid()
        )

        # # TEMP DEBUG — remove once diagnosed
        # print("=" * 60)
        # print("user_form:      ", user_form.is_valid(), user_form.errors)
        # print("student_form:   ", student_form.is_valid(), student_form.errors)
        # print("emergency:      ", emergency_formset.is_valid())
        # print("  form errors:  ", emergency_formset.errors)
        # print("  non-form:     ", emergency_formset.non_form_errors())
        # print("  deleted_objs: ", [f.cleaned_data.get('DELETE')
        #                            for f in emergency_formset.forms if f.cleaned_data])
        # print("medical_form:   ", medical_form.is_valid(), medical_form.errors)
        # print("forms_valid:    ", forms_valid)
        # print("POST DELETE keys:", {k: v for k,
        #                             v in request.POST.items() if 'DELETE' in k})
        # print("=" * 60)

        if password_submitted:
            forms_valid = forms_valid and password_form.is_valid()

        if forms_valid:
            user_form.save()
            student_form.save()

            instances = emergency_formset.save(commit=False)
            for instance in instances:
                instance.student = request.user.student_profile
                instance.save()
            emergency_formset.save_m2m()
            for deleted_object in emergency_formset.deleted_objects:

                tup = EmergencyContact.objects.filter(
                    student=student,
                    name=deleted_object.name
                )  # TODO : correct for a more robust deletion logic

                tup.first().delete()

            medical_instance = medical_form.save(commit=False)
            medical_instance.student = built['student']
            if medical_instance.odpc_consent_signed and not medical_instance.consent_date:
                medical_instance.consent_date = timezone.now()
            elif not medical_instance.odpc_consent_signed:
                medical_instance.consent_date = None
            medical_instance.save()

            if password_submitted:
                request.user.set_password(
                    password_form.cleaned_data['password'])
                request.user.save()
                # Without this, changing the password invalidates the
                # current session hash and logs the user out on their
                # very next request — right after they just changed it.
                update_session_auth_hash(request, request.user)

            messages.success(
                request,
                "Your account profile and settings have been updated."
            )
            return redirect('base-settings')

        return render(request, 'base/settings.html', {
            'tabs_config':       built['tabs_config'],
            'emergency_formset': emergency_formset,
            'active_tab':        self._active_tab(built, password_submitted),
        })

# ─────────────────────────────────────────────────────────────────────────────


class DataExportView(
    LoginRequiredMixin,
    StudentContextMixin,
    StudentProfileRequiredMixin,
    View,
):
    """Student downloads a JSON snapshot of their own data."""

    def get(self, request):
        try:
            student = self.get_student(request)
        except AttributeError:
            return JsonResponse(
                {'error': 'No profile data found for this user.'}, status=404
            )

        data = {
            'personal': {
                'full_name':      request.user.full_name,
                'email':          request.user.email,
                'telephone':      student.telephone_no,
                'national_id':    student.national_id,
                'religion':       student.religion,
                'domicile':       student.domicile,
                'marital_status': student.get_marital_status_display(),
            },
            'emergency_contacts': list(
                student.emergency_contacts.values(
                    'name', 'phone', 'email', 'relationship', 'address'
                )
            ),
            'academic': list(
                Enrollment.objects
                .filter(student=student)
                .values(
                    'curriculum__course__course_name',
                    'curriculum__course__course_code',
                    'status',
                )
            ),
            'parents': list(
                student.parents.values() if hasattr(student, 'parents') else []
            ),
        }

        response = JsonResponse(data, json_dumps_params={'indent': 2})
        safe_reg = student.registration_number.replace('/', '_')
        response['Content-Disposition'] = (
            f'attachment; filename="student_profile_{safe_reg}.json"'
        )
        return response
