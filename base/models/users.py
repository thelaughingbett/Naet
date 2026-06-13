# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0


from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .base import (
    BaseModelMixin,
    GENDER_CHOICES,

    id_type_choices,
)
from base.managers import (
    UserManager,
)


class User(BaseModelMixin, AbstractBaseUser, PermissionsMixin):
    STUDENT = 'student'
    STAFF = 'staff'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (STAFF,   'Staff'),
        (ADMIN,   'Admin'),
    ]

    first_name = models.CharField(max_length=78, null=True)
    last_name = models.CharField(max_length=78, null=True)
    surname = models.CharField(max_length=78, null=True)

    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)

    profile_picture = models.ImageField(
        null=True,
        blank=True,
        upload_to='profiles/',
        default='profiles/profile.jpg'
    )

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_activated = models.BooleanField(default=False)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname or ' '} {self.last_name}"

    @property
    def half_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}"
