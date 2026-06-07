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
from django.contrib import admin
from django import forms
from .models import (
    EmergencyContact,
    Student,
    School,
    Department,
    Programme,
    Tclass,
    User,
    Session,
    Reporting,
    FeeStructure,
    StudentFeeAccount,
    Payment,
    Curriculum
)
from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
    UsernameField
)

from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils.safestring import mark_safe


# register
class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'surname',
            'gender',
            'profile_picture',
            'email'
        )


class RegisterForm(forms.ModelForm):

    class Meta:
        model = Student
        fields = [
            'national_id',
            'religion',
            'nationality',
            'marital_status',
            'ethnicity',
            'date_of_birth',
            'place_of_birth',
        ]

        widgets = {
            'date_of_birth': forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }


class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'telephone_no',
            'domicile',
            'county',
            'sub_county',
            'location',
            'division',
            'constituency',
            'home_adress',
        ]
        labels = {
            'domicile': 'domicile/country of residence'
        }


class EmergencyContactInfoForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = [
            'name',
            'phone',
            'email',
            'relationship',
            'address'
        ]

        # TODO :  make this a formset


class EducationalInfoForm(forms.ModelForm):
    school = forms.ModelChoiceField(School.objects.all())
    department = forms.ModelChoiceField(Department.objects.all())
    programme = forms.ModelChoiceField(Programme.objects.all())

    class Meta:
        model = Student
        fields = (
            'registration_number',
            'school',
            'department',
            'programme',
            'stay',
            # 'hostel',  # TODO : conditional on stay being resident
        )
        labels = {
            'registration_number': 'University Admission Number'
        }


# login
class LoginForm(forms.ModelForm):
    emaile = forms.EmailField(max_length=255, min_length=14)

    class Meta:
        model = User
        fields = (
            'emaile',  # change this to student email
            'password'
        )

# Session


class CreateSessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = (
            'academic_year',
            'semester',
            'start_date',
            'end_date',
            'is_active'
        )
        widgets = {
            'start_date': forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            'end_date': forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),

        }


# Reporting
class ReportingForm(forms.ModelForm):
    class Meta:
        model = Reporting
        fields = (
            'session',
        )


# Fee Structure
class CreateFeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = (
            'Tclass',
            'session',
            'breakdown'
        )


# Payment
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = (

            'amount',
            'method',
            'transaction_ref',
        )


# admin site
class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=("Password"),
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a href="{}">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"
        field_classes = {"email": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get("password")
        if password:
            password.help_text = password.help_text.format("../password/")
        user_permissions = self.fields.get("user_permissions")
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related(
                "content_type"
            )


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """

    error_messages = {
        "password_mismatch": ("The two password fields didn’t match."),
    }
    password1 = forms.CharField(
        label=("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text=("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ("email",)
        field_classes = {"email": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs[
                "autofocus"
            ] = True

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password2", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CloneCurriculumAdminForm(forms.Form):
    target_session = forms.ModelChoiceField(
        queryset=Session.objects.all(),
        label="Destination Session",
        help_text="Select the academic period you want to  copy these into."
    )

    keep_professors = forms.BooleanField(
        required=False,
        initial=False,
        label="Retain Professors",
        help_text="Check this if the same lecturer's will teach these units next session "
    )


class BreakdownWidget(forms.Widget):
    template_name = "UNUSED"  # must be a non-None string

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                data = json.loads(value) if value else {}
            except json.JSONDecodeError:
                data = {}
        elif isinstance(value, dict):
            data = value
        else:
            data = {}

        widget_id = (attrs or {}).get('id', name)
        rows_html = ""
        for key, val in data.items():
            rows_html += f"""
            <div class="breakdown-row" style="display:flex;gap:8px;margin-bottom:6px;align-items:center;">
                <input type="text" name="{name}_key[]" value="{key}"
                    placeholder="Label (e.g. tuition)"
                    style="padding:6px 10px;border:1px solid #ccc;border-radius:4px;width:180px;font-size:13px;">
                <input type="number" name="{name}_value[]" value="{val}"
                    placeholder="Amount"
                    style="padding:6px 10px;border:1px solid #ccc;border-radius:4px;width:140px;font-size:13px;">
                <button type="button" onclick="this.closest('.breakdown-row').remove()"
                        style="background:#c0392b;color:white;border:none;padding:6px 10px;
                            border-radius:4px;cursor:pointer;font-size:13px;">✕</button>
            </div>"""

        return mark_safe(f"""  <!-- ADD THIS import: from django.utils.safestring import mark_safe -->
        <div style="margin-top:4px;">
            <div id="{widget_id}-rows">{rows_html}</div>
            <button type="button"
                    onclick="addBreakdownRow('{widget_id}', '{name}')"
                    style="margin-top:6px;padding:6px 14px;background:#2e7d32;color:white;
                        border:none;border-radius:4px;cursor:pointer;font-size:13px;">
                + Add item
            </button>
        </div>
        <script>
        function addBreakdownRow(widgetId, fieldName) {{
            const container = document.getElementById(widgetId + '-rows');
            const row = document.createElement('div');
            row.className = 'breakdown-row';
            row.style.cssText = 'display:flex;gap:8px;margin-bottom:6px;align-items:center;';
            row.innerHTML = `
                <input type="text" name="${{fieldName}}_key[]" placeholder="Label (e.g. hostel)"
                    style="padding:6px 10px;border:1px solid #ccc;border-radius:4px;width:180px;font-size:13px;">
                <input type="number" name="${{fieldName}}_value[]" placeholder="Amount"
                    style="padding:6px 10px;border:1px solid #ccc;border-radius:4px;width:140px;font-size:13px;">
                <button type="button" onclick="this.closest('.breakdown-row').remove()"
                        style="background:#c0392b;color:white;border:none;padding:6px 10px;
                            border-radius:4px;cursor:pointer;font-size:13px;">✕</button>
            `;
            container.appendChild(row);
        }}
        </script>""")


class BreakdownField(forms.JSONField):

    widget = BreakdownWidget

    def prepare_value(self, value):
        return value  # don't re-serialize to string for display

    def to_python(self, value):
        if isinstance(value, dict):
            return value  # already assembled by value_from_datadict
        return super().to_python(value)


class FeeStructureForm(forms.ModelForm):
    breakdown = BreakdownField()

    class Meta:
        model = FeeStructure   # your model
        fields = '__all__'
