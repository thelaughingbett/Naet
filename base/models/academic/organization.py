# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models

from ..base import BaseModelMixin,  WithSchoolMixin  # noqa: F401


class Institution(BaseModelMixin):
    active_session = models.ForeignKey(
        'Session',
        on_delete=models.DO_NOTHING
    )

    institution_name = models.CharField(max_length=123)
    logo = models.ImageField(upload_to='logo/')

    charter_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class School(BaseModelMixin):
    school_name = models.CharField(max_length=78)

    active_session = models.ForeignKey(
        'Session',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"school of {self.school_name}"


# TODO : reconsider the with school mixin
class Department(WithSchoolMixin, BaseModelMixin):
    department_name = models.CharField(max_length=123)

    def __str__(self):
        return f"Department of {self.department_name}"
