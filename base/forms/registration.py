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

from django.core.exceptions import ValidationError
import re
from django.forms import modelformset_factory
import json
from django.contrib import admin
from django import forms
from base.models import (
    EmergencyContact,
    Student,
    School,
    Department,
    Programme,
    User,
)


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
            'home_address',
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


        # TODO :  make this a formset✔️
EmergencyContactFormSet = modelformset_factory(
    EmergencyContact,
    form=EmergencyContactInfoForm,
    extra=2,
    max_num=2,
    min_num=2,
    validate_min=True
)


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


def _digits(value):
    return re.sub(r"\D", "", value or "")


class LookupForm(forms.Form):
    registration_number = forms.CharField(
        max_length=78,
        widget=forms.TextInput(attrs={
            "class": "entry__input", "placeholder": "e.g. 1101001/0001/26",
            "autocomplete": "off", "spellcheck": "false",
        }),
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "entry__input", "placeholder": "07XXXXXXXX",
            "autocomplete": "off", "inputmode": "tel",
        }),
    )

    student = None

    def clean(self):
        data = super().clean()
        reg = (data.get("registration_number") or "").strip()
        phone = _digits(data.get("phone_number"))
        if not reg or not phone:
            return data

        student = (
            Student.objects.select_related("user")
            .filter(registration_number__iexact=reg)
            .first()
        )
        stored = _digits(student.telephone_no) if student else ""
        # generic message: don't reveal whether the number exists
        if (not student or len(phone) < 9 or len(stored) < 9
                or phone[-9:] != stored[-9:]):
            raise ValidationError("No placement record matches those details.")
        if student.registration_completed_at:
            raise ValidationError(
                "Registration is already complete for this student. "
                "Contact the Registry if something is wrong."
            )
        self.student = student
        return data


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "profile_picture")


class EducationDetailsForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = (
            "name_of_secondary_school",
            "address_of_secondary_school",
            "stay",
        )
