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

from django.forms import BaseModelFormSet, modelformset_factory
import json
from django.contrib import admin
from django import forms
from base.models import (
    EmergencyContact,
    Student,
    User,
)
from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
    UsernameField
)

from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils.safestring import mark_safe


class LoginForm(forms.Form):
    email = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'you@university.ac.ke',
            'autocomplete': 'email',

        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'id': 'id_password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,  # ← must be False, unchecked = False not invalid
        initial=False,
    )


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'surname', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'surname': forms.TextInput(attrs={'placeholder': 'Surname'}),
            'profile_picture': forms.FileInput(attrs={'accept': 'image/*'}),
        }


class StudentSettingsForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'marital_status', 'name_of_spouse', 'spouse_contact',
            'id_type', 'national_id', 'religion', 'domicile', 'telephone_no'
        ]


class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = ['name', 'phone', 'email', 'relationship', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'relationship': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Physical Address'}),
        }


class BaseEmergencyContactFormSet(BaseModelFormSet):
    def clean(self):
        """Custom validation to ensure data bounds across the formset."""
        super().clean()
        # Count only forms that actually contain user data
        filled_forms = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                filled_forms += 1

        if filled_forms > 4:
            raise forms.ValidationError(
                "You can add a maximum of 4 emergency contacts.")


# Create the formset factory configuration
EmergencyContactFormSet = modelformset_factory(
    EmergencyContact,
    form=EmergencyContactForm,
    formset=BaseEmergencyContactFormSet,
    extra=0,      # Number of empty slots to display for adding new entries
    max_num=4,    # Strict absolute cap on total objects allowed
    can_delete=True  # Allows users to check a box to remove an existing contact
)


class ChangePasswordform(forms.Form):

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'id': 'current-password',
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
            'id': 'new-password',
        })
    )

    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'confirm-new-password',
            'id': 'password-confirm',
        })
    )
