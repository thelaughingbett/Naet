# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render

from base.forms import CloneCurriculumAdminForm
from .inlines import CurriculumProfessorInline
from .mixins import BaseAdmin
from base.models import (
    CommonUnitCurriculum,
    Course,
    Curriculum,
    Department,
    Lecturer,
    Session,
    Tclass,
)


class BulkProfessorAssignForm(forms.Form):
    """Assign a professor to all classes taking this common unit."""
    professor = forms.ModelChoiceField(
        queryset=Lecturer.objects.select_related('user'),
        label='Assign Professor'
    )


@admin.register(Course)
class CourseAdmin(BaseAdmin):
    filter_horizontal = ('prerequisites',)
    list_display = ['course_code', 'course_name', 'course_type', 'department']
    list_filter = ['course_type', 'department']
    inlines = [CurriculumProfessorInline]

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

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'prerequisites':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Course.objects.filter(
                    department=request.user.deptadmin_profile.department
                )
            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Course.objects.filter(
                    department__school=request.user.schooladmin_profile.school
                )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CommonUnitCurriculum)
class CommonUnitCurriculumAdmin(BaseAdmin):
    list_display = ['course', 'session',
                    'tclass_display', 'professors_display']
    list_filter = ['session', 'course__department']
    actions = ['bulk_assign_professor']

    def tclass_display(self, obj):
        return obj.Tclass.class_name
    tclass_display.short_description = 'Class'

    def professors_display(self, obj):
        return ', '.join(
            p.user.full_name or p.staff_number
            for p in obj.professor.all()
        )
    professors_display.short_description = 'Professors'

    def get_queryset(self, request):
        qs = CommonUnitCurriculum.objects.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile') or hasattr(user, 'schooladmin_profile'):
            return qs

        return qs.none()

    @admin.action(description='Assign professor to ALL classes for this course')
    def bulk_assign_professor(self, request, queryset):
        if 'apply' in request.POST:
            form = BulkProfessorAssignForm(request.POST)
            if form.is_valid():
                professor = form.cleaned_data['professor']
                updated = 0
                processed_courses = set()

                for curriculum in queryset:
                    course_session_key = (
                        curriculum.course_id, curriculum.session_id)
                    if course_session_key in processed_courses:
                        continue

                    siblings = Curriculum.objects.filter(
                        course=curriculum.course,
                        session=curriculum.session
                    )
                    for sibling in siblings:
                        sibling.professor.add(professor)
                        updated += 1

                    processed_courses.add(course_session_key)

                self.message_user(
                    request, f'Professor assigned to {updated} curriculum entries.')
                return

        form = BulkProfessorAssignForm()
        return render(
            request,
            'admin/bulk_assign_professor.html',
            {
                'form': form,
                'queryset': queryset,
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
                'courses': queryset.values(
                    'course__course_name',
                    'course__course_code'
                ).distinct(),
            }
        )


@admin.register(Curriculum)
class CurriculumAdmin(BaseAdmin):
    list_display = ('course', 'Tclass', 'session')
    list_filter = ('session', 'Tclass', 'course__course_type')
    actions = ['copy_to_current_session', 'bulk_clone_wizard']
    filter_horizontal = ('professor',)

    @admin.action(description='Clone selected structures to the active session')
    def copy_to_current_session(self, request, queryset):
        try:
            active_session = Session.objects.get(is_active=True)
            new_records = [
                Curriculum(course=req.course, Tclass=req.Tclass,
                           session=active_session)
                for req in queryset
            ]
            created = Curriculum.objects.bulk_create(
                new_records, ignore_conflicts=True)
            self.message_user(
                request,
                f"Cloned {len(created)} layouts to {active_session}.",
                messages.SUCCESS
            )
        except Session.DoesNotExist:
            self.message_user(
                request, "Please mark a session as active first.", messages.ERROR)

    @admin.action(description='Bulk clone')
    def bulk_clone_wizard(self, request, queryset):
        if request.method == 'POST' and 'apply' in request.POST:
            form = CloneCurriculumAdminForm(request.POST)
            if form.is_valid():
                target_session = form.cleaned_data['target_session']
                keep_professors = form.cleaned_data['keep_professors']

                new_records = []
                for req in queryset:
                    record = Curriculum(
                        course=req.course,
                        Tclass=req.Tclass,
                        session=target_session,
                    )
                    if keep_professors:
                        record.professor.set(req.professor.all())
                    new_records.append(record)

                cloned = Curriculum.objects.bulk_create(
                    new_records, ignore_conflicts=True)
                self.message_user(
                    request,
                    f"Cloned {len(cloned)} layouts to {target_session}.",
                    messages.SUCCESS
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = CloneCurriculumAdminForm()

        return render(
            request,
            'admin/clone_curriculum_intermediate.html',
            context={'items': queryset, 'form': form,
                     'action': 'bulk_clone_wizard'}
        )

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
