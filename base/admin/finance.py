# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from base.forms import FeeStructureForm
from .inlines import OverDraftInline, PaymentInline
from .mixins import BaseAdmin
from base.models import (
    FeeStructure,
    OverDraft,
    Payment,
    StudentFeeAccount,
    Tclass,
)


@admin.register(FeeStructure)
class FeeStructureAdmin(BaseAdmin):
    form = FeeStructureForm

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(
                Tclass__programme__department__school=user.schooladmin_profile.school
            )

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(
                Tclass__programme__department=user.deptadmin_profile.department
            )

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'Tclass':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(StudentFeeAccount)
class StudentFeeAccountAdmin(BaseAdmin):
    inlines = [PaymentInline, OverDraftInline]
    readonly_fields = ['balance', 'is_cleared', 'amount_billed']
    list_display = ['student', 'amount_billed',
                    'amount_paid', 'balance', 'is_cleared']


@admin.register(OverDraft)
class OverdraftAdmin(BaseAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(BaseAdmin):
    pass
