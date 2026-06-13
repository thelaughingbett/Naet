# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from base.models import (
    Curriculum,
    FeeStructure,
    Lecturer,
    OverDraft,
    Payment,
    Session,
)


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ['paid_at', 'transaction_ref',
                       'method', 'amount', 'phone_number', 'provider_ref']


class OverDraftInline(admin.StackedInline):
    model = OverDraft
    extra = 0
    fk_name = 'account'
    readonly_fields = ['amount', 'transaction', 'status']


class CurriculumInline(admin.StackedInline):
    model = Curriculum
    extra = 1
    fields = ['course', 'professor', 'session']


class FeeStructureInline(admin.StackedInline):
    model = FeeStructure
    extra = 0
    fields = ['session', 'breakdown']


class CurriculumProfessorInline(admin.TabularInline):
    model = Curriculum
    fields = ['Tclass', 'session', 'professor']
    readonly_fields = ['Tclass', 'session']
    extra = 0
    can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        try:
            active_session = Session.objects.get(is_active=True)
            return qs.filter(session=active_session)
        except Session.DoesNotExist:
            return qs.none()

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'professor':
            kwargs['queryset'] = Lecturer.objects.select_related(
                'user', 'department')
        return super().formfield_for_manytomany(db_field, request, **kwargs)
