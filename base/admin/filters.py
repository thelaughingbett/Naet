# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from base.models import Department


class DepartmentFilter(admin.SimpleListFilter):
    title = 'Department'
    parameter_name = 'department'

    def lookups(self, request, model_admin):
        user = request.user

        if user.is_superuser or hasattr(user, 'institutionadmin_profile'):
            departments = Department.objects.all()

        elif hasattr(user, 'schooladmin_profile'):
            departments = Department.objects.filter(
                school=user.schooladmin_profile.school
            )

        elif hasattr(user, 'deptadmin_profile'):
            departments = Department.objects.filter(
                record_id=user.deptadmin_profile.department.record_id
            )

        else:
            departments = Department.objects.none()

        return [(d.pk, d.name) for d in departments]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(department=self.value())
        return queryset
