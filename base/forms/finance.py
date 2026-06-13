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
