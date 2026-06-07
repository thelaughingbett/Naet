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

from django.contrib import admin
from django import forms
from django.forms import BaseInlineFormSet
from django.contrib import admin, messages
# from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
)
from django.http import Http404, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path
from django.db.models import Q


from .forms import (
    FeeStructureForm,
    UserChangeForm,
    UserCreationForm,
    CloneCurriculumAdminForm
)
from .models import (
    CommonUnitCurriculum,
    Enrollment,
    Student,
    User,
    Session,
    Curriculum,
    Course,
    School,
    SchoolAdmin,
    Department,
    Programme,
    Tclass,
    Lecturer,
    DeptAdmin,
    InstitutionAdmin,
    Reporting,
    FeeStructure,
    StudentFeeAccount,
    OverDraft,
    Payment,
    Result,
    Timetable,
    Hostel,
    HostelAllocation,
    HostelWarden,
    Deferment,
    DeferredStudent,
    ResidentStudent
)

admin.site.site_header = 'Student Portal Admin'
admin.site.site_title = 'Student Portal Admin'
admin.site.index_title = 'Welcome to the administration portal'

# admin.py
# scope foreignkey's


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
            # scope to dept admin's department if applicable
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
            # scope to dept admin's department if applicable
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
                    department=request.user.deptadmin_profile.department)

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Lecturer.objects.filter(
                    department__school=request.user.schooladmin_profile.school)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class HasDepartment:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'department':
            # scope to dept admin's department if applicable
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


@admin.register(Session)
class SessionAdmin(BaseAdmin):
    list_display = (
        'academic_year',
        'semester',
        'start_date',
        'end_date'
    )

    ordering = ["-academic_year"]

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
                f"Successfully transitioned system deployment to active target: {next_session}." f"Migrated {count} curriculum units automatically", messages.SUCCESS
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
                f"Sytem Compilation exception error: {str(e)}",
                messages.ERROR
            )
        return redirect('admin:base_session_changelist')

    def has_change_permission(self, request, obj=...):
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
class programmeAdmin(BaseAdmin):
    list_display = ['programme_name', 'department']

    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(
                department__school=user.schooladmin_profile.school
            )

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(
                department=user.deptadmin_profile.department
            )

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == 'current_class':
            # scope to dept admin's department if applicable
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department=request.user.deptadmin_profile.department
                )

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department__school=request.user.schooladmin_profile.school
                )

        if db_field.name == 'department':
            # scope to dept admin's department if applicable
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
    def get_queryset(self, request):
        qs = self.model._default_manager.get_queryset()
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            return qs

        if hasattr(user, 'schooladmin_profile'):
            return qs.filter(programme__department__school=user.schooladmin_profile.school)

        if hasattr(user, 'deptadmin_profile'):
            return qs.filter(programme__department=user.deptadmin_profile.department)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == 'programme':
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Programme.objects.filter(
                    department=request.user.deptadmin_profile.department)
            if hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Programme.objects.filter(
                    department__school=request.user.schooladmin_profile.school)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CurriculumProfessorInline(admin.TabularInline):
    model = Curriculum
    fields = ['Tclass', 'session', 'professor']
    readonly_fields = ['Tclass', 'session']  # don't let them change these here
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


@admin.register(Course)
class CourseAdmin(BaseAdmin):

    filter_horizontal = ('prerequisites',)
    list_display = ['course_code', 'course_name', 'type', 'department']
    list_filter = ['type', 'department']
    inlines = [CurriculumProfessorInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == 'department':
            # scope to dept admin's department if applicable
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
                    department=request.user.deptadmin_profile.department)

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Course.objects.filter(
                    department__school=request.user.schooladmin_profile.school)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class BulkProfessorAssignForm(forms.Form):
    """Assign a professor to all classes taking this common unit"""
    professor = forms.ModelChoiceField(
        queryset=Lecturer.objects.select_related('user'),
        label='Assign Professor'
    )


@admin.register(CommonUnitCurriculum)
class CommonUnitCurriculumAdmin(admin.ModelAdmin):
    list_display = [
        'course',
        'session',
        'tclass_display',
        'professors_display'
    ]
    list_filter = [
        'session',
        'course__department'
    ]
    actions = ['bulk_assign_professor']

    def tclass_display(self, obj):
        return obj.Tclass.class_name
    tclass_display.short_description = 'Class'

    def professors_display(self, obj):
        return ', '.join(
            p.user.get_full_name() or p.staff_number
            for p in obj.professor.all()
        )
    professors_display.short_description = 'Professors'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'course', 'session', 'Tclass'
        ).prefetch_related('professor__user')

    @admin.action(description='Assign professor to ALL classes for this course')
    def bulk_assign_professor(self, request, queryset):
        if 'apply' in request.POST:
            form = BulkProfessorAssignForm(request.POST)
            if form.is_valid():
                professor = form.cleaned_data['professor']
                # for each selected curriculum entry
                # find ALL siblings (same course + session) and assign
                updated = 0
                processed_courses = set()
                for curriculum in queryset:
                    course_session_key = (
                        curriculum.course_id,
                        curriculum.session_id
                    )
                    if course_session_key in processed_courses:
                        continue
                    # get all classes taking this course this session
                    siblings = Curriculum.objects.filter(
                        course=curriculum.course,
                        session=curriculum.session
                    )
                    for sibling in siblings:
                        sibling.professor.add(professor)
                        updated += 1
                    processed_courses.add(course_session_key)
                self.message_user(
                    request,
                    f'Professor assigned to {updated} curriculum entries.'
                )
                return
        # first pass — show the form
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
    list_display = ('course', 'Tclass', 'session', )
    list_filter = ('session', 'Tclass', 'course__type',)
    actions = ['copy_to_current_session', 'bulk_clone_wizard']
    filter_horizontal = (
        'professor',
    )

    @admin.action(description="clone Selected structures to the active session")
    def copy_to_current_session(self, request, queryset):
        try:
            active_session = Session.objects.get(is_active=True)
            new_records = []
            for req in queryset:
                record = Curriculum(
                    course=req.course,
                    Tclass=req.Tclass,
                    session=active_session,
                )

                record.professor.set(
                    req.professor
                ) if False else None

                new_records.append(
                    record
                )

            created = Curriculum.objects.bulk_create(
                new_records,
                ignore_conflicts=True
            )

            self.message_user(
                request, f"Cloned {len(created)} layouts to {active_session}.", messages.SUCCESS)
            pass
        except Session.DoesNotExist:
            self.message_user(
                request, f"please mark a session as active first .", messages.ERROR)
            pass

    @admin.action(description="bulk clone")
    def bulk_clone_wizard(self, request, queryset):
        print(request.POST)
        if request.method == "POST" and 'apply' in request.POST:
            form = CloneCurriculumAdminForm(request.POST)

            # selected_pks = request.POST.getlist('_selected_action')
            # actual_items = Curriculum.objects.filter(pk__in=selected_pks)

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

                    record.professor.set(
                        req.professor.all()
                    ) if keep_professors else None

                    new_records.append(
                        record
                    )
                cloned = Curriculum.objects.bulk_create(
                    new_records,
                    ignore_conflicts=True
                )
            self.message_user(
                request, f"Cloned {len(cloned)} layouts to {target_session}.", messages.SUCCESS)
            return HttpResponseRedirect(request.get_full_path())
        else:
            form = CloneCurriculumAdminForm()

        return render(
            request,
            'admin/clone_curriculum_intermediate.html',
            context={
                'items': queryset,
                'form': form,
                'action': 'bulk_clone_wizard'
            }
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
            # scope to dept admin's department if applicable
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department=request.user.deptadmin_profile.department
                )

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Tclass.objects.filter(
                    programme__department__school=request.user.schooladmin_profile.school
                )

        if db_field.name == 'course':
            # scope to dept admin's department if applicable
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
                    department=request.user.deptadmin_profile.department)

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Lecturer.objects.filter(
                    department__school=request.user.schooladmin_profile.school)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


# users
@admin.register(User)
class UserAdmin(BaseAdmin, BaseUserAdmin):
    # add_form_template = "admin/auth/user/add_form.html"
    # change_user_password_template = None
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (("Personal info"), {
         "fields": ("first_name", "last_name", "surname")}),
        (
            ("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    'role'
                ),
            },
        ),
        (("Important dates"), {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("email", "first_name", "last_name", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("first_name", "last_name", "email", 'surname')
    ordering = ("email",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )

    # list_editable = ('first_name',)

    def get_urls(self):
        from django.urls import path
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
            # staff in this school (via lecturer_profile → department → school)
            # admins in this school (via deptadmin_profile → department → school)
            return qs.filter(
                Q(
                    lecturer_profile__department__school=school
                ) |
                Q(
                    deptadmin_profile__department__school=school
                ) |
                Q(
                    schooladmin_profile__school=school
                ) |
                Q(
                    student_profile__class_entered__programme__department__school=school
                )
            ).distinct()

        if hasattr(user, 'deptadmin_profile'):
            department = user.deptadmin_profile.department
            # dept admin sees staff in their dept
            # and other dept admins in their dept
            # but NOT school admins or inst admins
            return qs.filter(
                Q(

                    lecturer_profile__department=department
                ) |
                Q(

                    deptadmin_profile__department=department
                ) |
                Q(
                    student_profile__class_entered__programme__department=department
                )
            ).distinct()

        if hasattr(user, 'lecturer_profile'):
            # staff see only other staff in their department
            # not admins
            return qs.filter(
                role=User.STAFF,
                lecturer_profile__department=user.lecturer_profile.department
            )

        return qs.none()


@admin.register(Student)
class StudentAdmin(BaseAdmin):
    # filter_horizontal = ('enrollments',)
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

        # if db_field.name == 'user':
        #     # only show users with student role
        #     kwargs['queryset'] = User.objects.filter(role=User.STUDENT)

        if db_field.name == 'class_entered':
            # scope to dept admin's department if applicable
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
                    # only show curriculum for the student's class and active session
                    kwargs['queryset'] = Curriculum.objects.filter(
                        Tclass=student.class_entered,
                        session__is_active=True
                    ).select_related('course', 'session')
                except Student.DoesNotExist:
                    kwargs['queryset'] = Curriculum.objects.none()
            else:
                # new student — show active session curriculum only
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
            # only show users with student role
            kwargs['queryset'] = User.objects.filter(role='staff'
                                                     ).exclude(record_id=request.user.record_id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
            return qs.filter(
                department=user.deptadmin_profile.department
            )

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # if db_field.name == 'user':
        #     # only show users with student role

        #     if hasattr(request.user, 'deptadmin_profile'):
        #         kwargs['queryset'] = User.objects.filter(
        #             lecturer_profile__department=request.user.deptadmin_profile.department)

        #     elif hasattr(request.user, 'schooladmin_profile'):
        #         kwargs['queryset'] = User.objects.filter(
        #             lecturer_profile__department__school=request.user.schooladmin_profile.school
        #         )

        if db_field.name == 'department':
            # scope to dept admin's department if applicable
            if hasattr(request.user, 'deptadmin_profile'):
                kwargs['queryset'] = Department.objects.filter(
                    record_id=request.user.deptadmin_profile.department.record_id
                )

            elif hasattr(request.user, 'schooladmin_profile'):
                kwargs['queryset'] = Department.objects.filter(
                    school=request.user.schooladmin_profile.school
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


#####

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
            # scope to dept admin's department if applicable
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
    pass


@admin.register(OverDraft)
class OverdraftAdmin(BaseAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(BaseAdmin):
    pass


@admin.register(Result)
class ResultAdmin(BaseAdmin):
    pass


@admin.register(Timetable)
class TimetableAdmin(BaseAdmin):
    pass


@admin.register(Enrollment)
class EnrollmentAdmin(BaseAdmin):
    pass


@admin.register(Hostel)
class HostelAadmin(BaseAdmin):
    pass


@admin.register(HostelAllocation)
class HostelAllocationAdmin(BaseAdmin):
    pass


@admin.register(HostelWarden)
class HostelWardenAdmin(BaseAdmin):
    pass


@admin.register(Deferment)
class DefermentAdmin(BaseAdmin):
    pass


@admin.register(DeferredStudent)
class DeferredStudentAdmin(BaseAdmin):
    list_display = ['registration_number', 'user', 'days_deferred']
    actions = ['reinstate_students']

    def reinstate_students(self, request, queryset):
        for student in queryset:
            student.reinstate()
    reinstate_students.short_description = "Reinstate selected students"


@admin.register(ResidentStudent)
class ResidentStudentAdmin(BaseAdmin):
    pass


@admin.register(Reporting)
class ReportingAdmin(BaseAdmin):
    pass

# test paswords
# admin - admin@email.com -admin
# dept-admin - deptadmin@password
# school-admin - password123@schooladmin
