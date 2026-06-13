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
