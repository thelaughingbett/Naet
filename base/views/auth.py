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


from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from decouple import config

from django.contrib import messages
from django.shortcuts import (
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.contrib.auth import (
    authenticate,
    login,
    logout
)

from base.forms import (
    LoginForm,
)
# TODO : check breaking duplicate emergencycontact formset in auth and registration
from base.forms.auth import (
    EmergencyContactFormSet,
    StudentSettingsForm,
    UserSettingsForm,
    ChangePasswordform
)
from .base import StudentContextMixin, StudentProfileRequiredMixin
from base.models import (
    EmergencyContact,
    Student,
    Lecturer,
    DeptAdmin,
    ItStaff,
    Enrollment
)

from django.db import models


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('base-index')
        return render(request, 'base/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)

        if form.is_valid():
            input_login = form.cleaned_data['email'].strip()
            password = form.cleaned_data['password']

            user = authenticate(
                request, username=input_login, password=password)

            if not user:
                resolved_email = None

                student_match = Student.objects.filter(
                    models.Q(registration_number__iexact=input_login) |
                    models.Q(school_email__iexact=input_login)
                ).select_related('user').first()

                if student_match and hasattr(student_match, 'user') and student_match.user:
                    resolved_email = student_match.user.email
                else:
                    for staff_model in [Lecturer, DeptAdmin, ItStaff]:
                        match = staff_model.objects.filter(
                            models.Q(staff_number__iexact=input_login)
                        ).select_related('user').first()

                        if match and hasattr(match, 'user') and match.user:
                            resolved_email = match.user.email
                            break

                if resolved_email:
                    user = authenticate(
                        request, username=resolved_email, password=password)

            if user:
                login(request, user)
                if form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(60 * 60 * 24 * 30)
                else:
                    request.session.set_expiry(0)
                return redirect(request.GET.get('next', 'base-index'))

            form.add_error(None, "Invalid credentials or password.")

        return render(request, 'base/login.html', {'form': form})


class LogoutView(View):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def post(self, request):
        logout(request)
        return redirect(reverse('base-login'))

# TODO :  cross check this code for bugs especially on post 👇🏿👇🏿


class SettingsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config('LOGIN_URL') + '?next=settings'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get_tab_data(self, request, post_data=None, files_data=None):
        """Helper to build all form instances bound to active records."""
        user = request.user
        # Assuming Student is accessible via related name or mixin
        student = self.get_student(request)
        queryset = EmergencyContact.objects.filter(student=student)

        # Initialize forms with conditional POST data binding
        user_form = UserSettingsForm(post_data, files_data, instance=user)
        student_form = StudentSettingsForm(post_data, instance=student)
        emergency_formset = EmergencyContactFormSet(
            post_data, queryset=queryset, prefix='emergency')

        # This structural array powers our dynamic frontend tabs completely!
        tabs_config = [
            {
                'id': 'general',
                'title': 'General Info',
                'form': user_form,
                'is_formset': False,
                'legend': 'General Profile Details'
            },
            {
                'id': 'personal',
                'title': 'Personal Info',
                'form': student_form,
                'is_formset': False,
                'legend': 'Personal Settings & Identification'
            },
            {
                'id': 'emergency',
                'title': 'Emergency Contacts',
                'formset': emergency_formset,
                'is_formset': True,
                'legend': 'Emergency Contact Info (Maximum 4)'
            },
            {
                'id': 'password',
                'title': "Change Password",
                'form': ChangePasswordform(),
                'is_formset': False,
                'legend': 'Change password'
            }
        ]

        return tabs_config, user_form, student_form, emergency_formset

    def get(self, request):
        tabs_config, _, _, _ = self.get_tab_data(request)
        return render(request, 'base/settings.html', {'tabs_config': tabs_config})

    def post(self, request):
        tabs_config, user_form, student_form, emergency_formset = self.get_tab_data(
            request, request.POST, request.FILES
        )

        # Validate all dynamic form components simultaneously
        if (
            user_form.is_valid() and
            student_form.is_valid() and
            emergency_formset.is_valid()
        ):
            user_form.save()
            student_form.save()

            # Process multi-row formset modifications safely
            instances = emergency_formset.save(commit=False)
            for instance in instances:
                instance.student = request.user.student
                instance.save()

            emergency_formset.save_m2m()
            for deleted_object in emergency_formset.deleted_objects:
                deleted_object.delete()

            messages.success(
                request,
                "Your account profile and settings have been updated."
            )
            return redirect('base-settings')
        context = {
            'tabs_config': tabs_config
        }
        return render(request, 'base/settings.html', context)


class DataExportView(
    LoginRequiredMixin,
    StudentContextMixin,
    StudentProfileRequiredMixin,
    View
):
    """Student safely downlinks a clean snapshot copy of their own data as a secure application/json file payload tracking dump."""

    def get(self, request):
        # Defensively resolve student profile link records safely across context mixers mapping systems
        try:
            student = self.get_student(request)
        except AttributeError:
            return JsonResponse({'error': 'No profile data found for this active user account context.'}, status=404)

        # Pull collections with pre-targeted values mappings directly from standard relational lookups
        data = {
            'personal': {
                'full_name': request.user.full_name,
                'email': request.user.email,
                'telephone': student.telephone_no,
                'national_id': student.national_id,
                'religion': student.religion,
                'domicile': student.domicile,
                # Expose human readable text mappings automatically
                'marital_status': student.get_marital_status_display(),
            },
            'emergency_contacts': list(student.emergency_contacts.values(
                'name', 'phone', 'email', 'relationship', 'address'
            )),
            'academic': list(
                Enrollment.objects.filter(student=student)
                .values(
                    'curriculum__course__course_name',
                    'curriculum__course__course_code',
                    'status'  # Use the exact column name defined on your intermediate enrollment table
                )
            ),
            'parents': list(student.parents.all().values(
                # Fallback space placeholder: plug additional account processing structures here cleanly if required
            ) if hasattr(student, 'parents') else []),
        }

        # Initialize native JsonResponse with proper content-type, encoding parameters, and safety layers
        # Formats nested trees cleanly with beautiful formatting indent lines natively
        response = JsonResponse(data, json_dumps_params={'indent': 2})

        # Force browser to process stream chunk as file download buffer stream
        response[
            'Content-Disposition'] = f'attachment; filename="student_profile_{student.registration_number.replace("/", "_")}.json"'
        return response
