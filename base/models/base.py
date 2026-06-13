# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import uuid

from django.db import models


GENDER_CHOICES = [
    ("M", "Male"),
    ("F", "Female"),
]

id_type_choices = [
    ('national', 'National ID'),
    ('passport', 'Passport'),
    ('birthCert', 'Birth Certificate'),
]


class TimeStampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModelMixin(TimeStampedMixin):
    record_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True


class hasUserMixin(models.Model):
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='%(class)s_profile'
    )

    class Meta:
        abstract = True


class StaffUserMixin(hasUserMixin):
    staff_number = models.CharField(max_length=20, unique=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.staff_number} - {self.user}"

    def save(self, *args, **kwargs):
        self.user.is_staff = True
        self.user.save()
        super().save(*args, **kwargs)


class WithDepartmentMixin(models.Model):
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='%(class)s_set'
    )

    class Meta:
        abstract = True


class WithSchoolMixin(models.Model):
    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        related_name='%(class)s_set'
    )

    class Meta:
        abstract = True


class WithClassMixin(models.Model):
    Tclass = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


# class HasClassMixin(models.Model):
#     tclass = models.ForeignKey(
#         'TClass',
#         on_delete=models.DO_NOTHING
#     )

#     class Meta:
#         abstract = True
#     pass
