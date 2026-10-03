# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
from django.db import models
from django.core.validators import RegexValidator

from ..base import BaseModelMixin, WithSchoolMixin  # noqa: F401


phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{7,15}$',
    message="Enter a valid phone number (7 to 15 digits, optionally starting with +).",
)


class ContactInfoMixin(models.Model):
    """
    Reusable contact information fields.
    Mix this into any model that needs an email/phone/address —
    Institution, School, Department, etc.
    """

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[phone_validator]
    )
    alternate_phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[phone_validator]
    )

    address = models.TextField(blank=True, null=True)
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    website = models.URLField(blank=True, null=True)

    class Meta:
        abstract = True


class Institution(ContactInfoMixin, BaseModelMixin):
    active_session = models.ForeignKey(
        'Session',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True
    )

    institution_name = models.CharField(max_length=123)
    logo = models.ImageField(upload_to='logo/')

    charter_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # class Meta:
    #     abstract = True

    @property
    def name(self):
        return self.department_name

    @name.setter
    def set_name(self, value):
        name = value.strip()
        self.institution_name = name

    def __str__(self):
        return f"{self.institution_name}"


class School(ContactInfoMixin, BaseModelMixin):
    school_name = models.CharField(max_length=78)

    active_session = models.ForeignKey(
        'Session',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    @property
    def name(self):
        return self.department_name

    @name.setter
    def set_name(self, value):
        name = value.strip()
        self.school_name = name

    def __str__(self):
        return f"school of {self.school_name}"


# TODO : reconsider the with school mixin
class Department(ContactInfoMixin, WithSchoolMixin, BaseModelMixin):
    department_name = models.CharField(max_length=123)

    @property
    def name(self):
        return self.department_name

    @name.setter
    def set_name(self, value):
        name = value.strip()
        self.department_name = name

    def __str__(self):
        return f"Department of {self.department_name}"


class Office(ContactInfoMixin, BaseModelMixin):
    """
    Non-academic, institution-wide administrative units —
    Admissions, Student Support, Registrar, Bursar, IT Helpdesk, etc.
    Distinct from Department, which is scoped to a School.
    """

    class OfficeType(models.TextChoices):
        ADMISSIONS = 'admissions', 'Admissions'
        STUDENT_SUPPORT = 'student_support', 'Student Support'
        REGISTRAR = 'registrar', 'Registrar'
        BURSAR = 'bursar', 'Bursar / Finance'
        IT_HELPDESK = 'it_helpdesk', 'IT Helpdesk'
        FINANCE = 'finance', "Finance Office"
        LIBRARY = 'library', 'Library'
        HR = 'hr', 'Human Resources'
        EXAM = "exam", "Exam office"
        OTHER = 'other', 'Other'

    office_name = models.CharField(max_length=123)

    office_type = models.CharField(
        max_length=30,
        choices=OfficeType.choices,
        default=OfficeType.OTHER,
    )

    institution = models.ForeignKey(
        'Institution',
        on_delete=models.CASCADE,
        related_name='offices',
    )

    @property
    def name(self):
        return self.office_name

    @name.setter
    def set_name(self, value):
        name = value.strip()
        self.office_name = name

    @property
    def type(self):
        return self.office_type

    @type.setter
    def set_type(self, value):
        office_type = value.strip()

        if office_type not in self.OfficeType.values:
            raise ValueError(
                f"Invalid office type '{office_type}'. "
                f"Choose from: {', '.join(self.OfficeType.values)}"
            )

        self.office_type = office_type

    def __str__(self):
        return self.office_name
