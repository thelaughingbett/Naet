# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models

from ..base import BaseModelMixin


class IDCard(BaseModelMixin):
    student = models.OneToOneField(
        'Student',
        on_delete=models.CASCADE,
        related_name="id_card"
    )
    card_number = models.CharField(max_length=30, unique=True)
    issued_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(
        upload_to="registrar/id_photos/",
        blank=True,
        null=True
    )

    # an easily printable copy of the physical id issued to the student
    file = models.FileField(
        upload_to="registrar/id_file",
        blank=True,
        null=True
    )  # TODO :  in clean make this file named to students name,reg_no and date issued ,also make sure image exist's
