# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import re

from django.forms import BaseModelFormSet, modelformset_factory
from django import forms
from base.models import (
    EmergencyContact,
    Student,
    StudentMedicalProfile,
    User,
)

from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation


# Letters, spaces, hyphens, apostrophes — covers hyphenated/apostrophe'd
# names (e.g. "Achieng'", "Ndung'u", "Mary-Anne") without opening the door
# to digits or symbols in a "text" field.
NAME_PATTERN = r"[A-Za-z' \-]+"


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
        required=False,
        initial=False,
    )


class UserSettingsForm(forms.ModelForm):

    # First/last name are set at admission and shown for reference only.
    # `disabled=True` isn't just a display trick — Django ignores whatever
    # comes back in POST for a disabled field and always keeps the
    # field's initial (the instance's current) value, so a hand-crafted
    # request can't change them either. Surname is the only editable
    # name field, since it's the one that's commonly not captured at
    # admission time.

    first_name = forms.CharField(
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'read-only-box-input'}),
    )
    last_name = forms.CharField(
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'read-only-box-input'}),
    )
    surname = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Surname',
            'class': 'text-only-input',
            'pattern': NAME_PATTERN,
            'title': 'Letters, spaces, hyphens and apostrophes only',
        }),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'surname', 'profile_picture']

    def clean_surname(self):
        surname = (self.cleaned_data.get('surname') or '').strip()
        if surname and not re.fullmatch(NAME_PATTERN, surname):
            raise ValidationError(
                "Surname can only contain letters, spaces, hyphens and apostrophes."
            )
        return surname


class StudentSettingsForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'marital_status', 'name_of_spouse', 'spouse_contact',
            'id_type', 'national_id', 'religion', 'domicile', 'telephone_no'
        ]
        widgets = {
            'name_of_spouse': forms.TextInput(attrs={
                'class': 'text-only-input',
                'pattern': NAME_PATTERN,
                'title': 'Letters, spaces, hyphens and apostrophes only',
            }),
        }

    def clean_name_of_spouse(self):
        name = (self.cleaned_data.get('name_of_spouse') or '').strip()
        if name and not re.fullmatch(NAME_PATTERN, name):
            raise ValidationError(
                "Spouse's name can only contain letters, spaces, hyphens and apostrophes."
            )
        return name


class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = [

            'name',
            'phone',
            'email',
            'relationship',
            'address',
        ]
        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control text-only-input',
                'placeholder': 'Full Name',
                'pattern': NAME_PATTERN,
                'title': 'Letters, spaces, hyphens and apostrophes only',
            }),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'relationship': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Physical Address'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if name and not re.fullmatch(NAME_PATTERN, name):
            raise ValidationError(
                "Name can only contain letters, spaces, hyphens and apostrophes."
            )
        return name


class BaseEmergencyContactFormSet(BaseModelFormSet):
    def clean(self):
        """Custom validation to ensure data bounds across the formset."""
        super().clean()
        filled_forms = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                filled_forms += 1

        if filled_forms > 4:
            raise forms.ValidationError(
                "You can add a maximum of 4 emergency contacts.")


EmergencyContactFormSet = modelformset_factory(
    EmergencyContact,
    form=EmergencyContactForm,
    formset=BaseEmergencyContactFormSet,
    extra=0,
    max_num=4,
    can_delete=True
)


class StudentMedicalProfileForm(forms.ModelForm):
    class Meta:
        model = StudentMedicalProfile
        fields = [
            'blood_group', 'known_allergies', 'chronic_conditions',
            'requires_special_accommodation', 'accommodation_notes',
            'odpc_consent_signed',
        ]
        widgets = {
            'known_allergies': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Penicillin, peanuts — or "None Registered"',
            }),
            'chronic_conditions': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Asthma, Diabetes, Epilepsy — or "None"',
            }),
            'accommodation_notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe the accommodation needed (required if the box above is checked)',
            }),
        }
        labels = {
            'requires_special_accommodation':
                'I require a special accommodation (e.g. accessible hostel room, exam time extension)',
            'odpc_consent_signed':
                'I consent to the university processing this medical information under the Data Protection Act',
        }
        # blood_group / known_allergies / chronic_conditions /
        # requires_special_accommodation / accommodation_notes handled
        # above. The model's `clean()` (which requires accommodation_notes
        # whenever requires_special_accommodation is True) still fires
        # automatically via ModelForm._post_clean(), so that rule is
        # enforced without repeating it here.


class ChangePasswordform(forms.Form):
    old_password = forms.CharField(
        label='Current password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'id': 'current-password',
        })
    )
    password = forms.CharField(
        label='New password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
            'id': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm new password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
            'id': 'password-confirm',
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if self.user and old_password and not self.user.check_password(old_password):
            raise ValidationError("Your current password is incorrect.")
        return old_password

    def clean(self):
        cleaned = super().clean()
        old_password = cleaned.get('old_password')
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')

        any_filled = any([old_password, password, password_confirm])

        if any_filled and not old_password:
            self.add_error(
                'old_password', "Please enter your current password.")
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "New passwords do not match.")
        elif password and not password_confirm:
            self.add_error('password_confirm',
                           "Please confirm your new password.")
        elif password_confirm and not password:
            self.add_error('password', "Please enter your new password.")

        if password:
            try:
                password_validation.validate_password(password, self.user)
            except ValidationError as e:
                self.add_error('password', e)

        return cleaned
