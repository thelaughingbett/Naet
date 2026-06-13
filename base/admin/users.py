# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.db.models import Q
from django.urls import path

from base.forms import UserChangeForm, UserCreationForm
from .mixins import BaseAdmin
from base.models import (
    Curriculum,
    Department,
    DeptAdmin,
    InstitutionAdmin,
    Lecturer,
    SchoolAdmin,
    Student,
    Tclass,
    User,
)


@admin.register(User)
class UserAdmin(BaseAdmin, BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'surname')}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions', 'role'
            )
        }),
        ('Important dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('first_name', 'last_name', 'email', 'surname')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<id>/password/',
                self.admin_site.admin_view(self.user_change_password),
                name='auth_user_password_change',
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            school = user.schooladmin_profile.school
            return qs.filter(
                Q(lecturer_profile__department__school=school) |
                Q(deptadmin_profile__department__school=school) |
                Q(schooladmin_profile__school=school) |
                Q(student_profile__class_entered__programme__department__school=school)
            ).distinct()

        if hasattr(user, 'deptadmin_profile'):
            department = user.deptadmin_profile.department
            return qs.filter(
                Q(lecturer_profile__department=department) |
                Q(deptadmin_profile__department=department) |
                Q(student_profile__class_entered__programme__department=department)
            ).distinct()

        if hasattr(user, 'lecturer_profile'):
            return qs.filter(
                role=User.STAFF,
                lecturer_profile__department=user.lecturer_profile.department
            )

        return qs.none()


@admin.register(Student)
class StudentAdmin(BaseAdmin):
    list_select_related = ['user', 'class_entered', 'class_entered__programme']

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(
                class_entered__programme__department__school=user.schooladmin_profile.school
            )

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(
                class_entered__programme__department=user.deptadmin_profile.department
            )

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'class_entered':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'enrollments':
            student_id = request.resolver_match.kwargs.get('object_id')

            if student_id:
                try:
                    student = Student.objects.get(pk=student_id)
                    kwargs['queryset'] = Curriculum.objects.filter(
                        Tclass=student.class_entered,
                        session__is_active=True
                    ).select_related('course', 'session')
                except Student.DoesNotExist:
                    kwargs['queryset'] = Curriculum.objects.none()
            else:
                if hasattr(request.user, 'deptadmin_profile'):
                    kwargs['queryset'] = Curriculum.objects.filter(
                        session__is_active=True,
                        Tclass__programme__department=request.user.deptadmin_profile.department
                    ).select_related('course', 'session')
                if hasattr(request.user, 'schooladmin_profile'):
                    kwargs['queryset'] = Curriculum.objects.filter(
                        session__is_active=True,
                        Tclass__programme__department__school=request.user.schooladmin_profile.school
                    ).select_related('course', 'session')

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Lecturer)
class LecturerAdmin(BaseAdmin):
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


@admin.register(InstitutionAdmin)
class InstitutionAdminAdmin(BaseAdmin):
    pass


@admin.register(SchoolAdmin)
class SchoolAdminAdmin(BaseAdmin):
    pass


@admin.register(DeptAdmin)
class DeptAdminAdmin(BaseAdmin):
    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(department__school=user.schooladmin_profile.school)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(role='staff').exclude(
                record_id=request.user.record_id
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
