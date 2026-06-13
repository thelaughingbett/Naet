# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from base.models import (
    Course,
    Department,
    Lecturer,
    Programme,
    School,
    Tclass,
)


class ScopedAdminMixin:
    """Restrict queryset based on the logged-in user's role/dept/school."""

    def _get_dept(self, user):
        if hasattr(user, 'deptadmin_profile'):
            return user.deptadmin_profile.department
        return None

    def _get_school(self, user):
        if hasattr(user, 'schooladmin_profile'):
            return user.schooladmin_profile.school
        return None


class HasTclassMixin:
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


class HasCourseMixin:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Course.objects.filter(
                    department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Course.objects.filter(
                    department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class HasSchoolMixin:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school':
            if hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = School.objects.filter(
                    record_id=request.user.schooladmin_profile.school.record_id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class HasLecturerMixin:
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'professor':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Lecturer.objects.filter(
                    department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Lecturer.objects.filter(
                    department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class HasDepartmentMixin:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
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


class BaseAdmin(ScopedAdminMixin, admin.ModelAdmin):

    def _perm(self, request, action):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        return request.user.has_perm(f'{app_label}.{action}_{model_name}')

    def has_view_permission(self, request, obj=None):
        return self._perm(request, 'view')

    def has_add_permission(self, request):
        return self._perm(request, 'add')

    def has_change_permission(self, request, obj=None):
        return self._perm(request, 'change')

    def has_delete_permission(self, request, obj=None):
        return self._perm(request, 'delete')
