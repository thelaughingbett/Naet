# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
import magic
import os
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
    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class BaseModelMixin(TimeStampedMixin):
    record_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    deleted = models.BooleanField(default=False)

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


class ValidatedFileMixin(models.Model):
    """
    Abstract mixin for any model that attaches a validated file.
    Subclasses override `allowed_mime_types` (or `get_allowed_mime_types()`
    for per-instance rules, e.g. per-agency) — the extension + magic-number
    check itself is shared.
    """

    file = models.FileField(upload_to='attachments/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    allowed_mime_types = {
        '.pdf': ['application/pdf'],
        '.png': ['image/png'],
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
    }
    max_size_bytes = 25 * 1024 * 1024  # 25MB default, override per subclass if needed

    class Meta:
        abstract = True

    def get_allowed_mime_types(self) -> dict:
        return self.allowed_mime_types

    def clean(self):
        super().clean()
        if not self.file:
            return

        if self.file.size > self.max_size_bytes:
            raise ValidationError(
                f"File is too large ({self.file.size // 1024 // 1024}MB). "
                f"Maximum is {self.max_size_bytes // 1024 // 1024}MB."
            )

        allowed = self.get_allowed_mime_types()
        ext = os.path.splitext(self.file.name)[1].lower()

        if ext not in allowed:
            raise ValidationError(
                f"Unsupported file format '{ext}'. Accepted: {', '.join(allowed.keys())}."
            )

        self.file.seek(0)
        header = self.file.read(2048)
        self.file.seek(0)
        detected = magic.from_buffer(header, mime=True)

        if detected not in allowed[ext]:
            raise ValidationError(
                f"File content does not match its extension. Detected '{detected}' for '{ext}'."
            )

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)
