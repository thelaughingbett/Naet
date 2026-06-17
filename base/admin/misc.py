# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from .mixins import BaseAdmin
from base.models import (
    Deferment,
    DeferredStudent,
    Enrollment,
    Reporting,
    Result,
    Timetable,
)


@admin.register(Result)
class ResultAdmin(BaseAdmin):
    pass


@admin.register(Enrollment)
class EnrollmentAdmin(BaseAdmin):
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
    reinstate_students.short_description = 'Reinstate selected students'


@admin.register(Reporting)
class ReportingAdmin(BaseAdmin):
    pass
