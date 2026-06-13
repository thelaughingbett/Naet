# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path

from .inlines import CurriculumInline, FeeStructureInline
from .mixins import BaseAdmin
from base.models import (
    Department,
    Programme,
    School,
    Session,
    Tclass,
)


@admin.register(Session)
class SessionAdmin(BaseAdmin):
    list_display = ('academic_year', 'semester', 'start_date', 'end_date')
    ordering = ['-academic_year']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'rollover/',
                self.admin_site.admin_view(self.trigger_rollover_view),
                name='session-rollover'
            )
        ]
        return custom_urls + urls

    def trigger_rollover_view(self, request):
        try:
            next_session, count = Session.rollover_academic_session(
                keep_professor=False)
            self.message_user(
                request,
                f"Successfully transitioned system deployment to active target: {next_session}."
                f" Migrated {count} curriculum units automatically",
                messages.SUCCESS
            )
        except Session.DoesNotExist:
            self.message_user(
                request,
                "Rollover aborted: no current active session found in database",
                messages.ERROR
            )
        except Exception as e:
            self.message_user(
                request,
                f"System Compilation exception error: {str(e)}",
                messages.ERROR
            )
        return redirect('admin:base_session_changelist')

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile') or hasattr(user, 'schooladmin_profile'):
            return qs

        return qs.none()


@admin.register(School)
class SchoolAdminAdmin(BaseAdmin):
    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        return qs.none()


@admin.register(Department)
class DepartmentAdmin(BaseAdmin):
    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(school=user.schooladmin_profile.school)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school':
            if hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = School.objects.filter(
                    record_id=request.user.schooladmin_profile.school.record_id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Programme)
class ProgrammeAdmin(BaseAdmin):
    list_display = ['programme_name', 'department']

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(department__school=user.schooladmin_profile.school)

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(department=user.deptadmin_profile.department)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'current_class':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department__school=request.user.schooladmin_profile.school
                )

        if db_field.name == 'department':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Department.objects.filter(
                    record_id=request.user.deptadmin_profile.department.record_id
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Department.objects.filter(
                    school=request.user.schooladmin_profile.school
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Tclass)
class TclassAdmin(BaseAdmin):
    inlines = [CurriculumInline, FeeStructureInline]
    list_display = ['class_name', 'programme']

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(
                programme__department__school=user.schooladmin_profile.school
            )

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(programme__department=user.deptadmin_profile.department)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'programme':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Programme.objects.filter(
                    department=request.user.deptadmin_profile.department
                )
            if hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Programme.objects.filter(
                    department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
