# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models

from .base import (
    BaseModelMixin,
    StaffUserMixin,
    WithDepartmentMixin,
    WithSchoolMixin,
)


class Lecturer(WithDepartmentMixin, StaffUserMixin, BaseModelMixin):
    academic_titles_abbreviated = [
        ("Graduate Assistant",   "GA"),
        ("Teaching Assistant",   "TA"),
        ("Tutorial Fellow",      "TF"),
        ("Assistant Lecturer",   "Asst. Lec."),
        ("Junior Lecturer",      "Jr. Lec."),
        ("Lecturer",             "Lec."),
        ("Senior Lecturer",      "Snr. Lec."),
        ("Associate Professor",  "Assoc. Prof."),
        ("Professor",            "Prof."),
        ("Full Professor",       "Full Prof."),
        ("Distinguished Professor", "Dist. Prof."),
        ("Emeritus Professor",   "Prof. Emeritus"),
        ("Adjunct Lecturer",     "Adj. Lec."),
        ("Visiting Lecturer",    "Vis. Lec."),
        ("Guest Lecturer",       "Guest Lec."),
        ("Part-Time Lecturer",   "PT Lec."),
        ("Head of Department",   "HOD"),
        ("Dean of Faculty",      "Dean"),
        ("Director of School",   "Director"),
        ("Chaired Professor",    "Chair Prof."),
    ]

    title = models.CharField(
        max_length=23,
        choices=academic_titles_abbreviated,
        default='Lecturer'
    )

    def __str__(self):
        return f"{self.staff_number} - {self.user}"

    @property
    def name(self):
        return f"{self.get_title_display()}{self.user.half_name}"


class DeptAdmin(BaseModelMixin, StaffUserMixin, WithDepartmentMixin):
    pass


class SchoolAdmin(BaseModelMixin, StaffUserMixin, WithSchoolMixin):
    pass


class InstitutionAdmin(StaffUserMixin, BaseModelMixin):
    pass


class HostelWarden(StaffUserMixin, BaseModelMixin):
    hostel = models.ForeignKey(
        'Hostel',
        on_delete=models.CASCADE,
        null=True,
    )


class ItStaff(StaffUserMixin, BaseModelMixin):
    pass


class FinanceStaff(StaffUserMixin, BaseModelMixin):
    pass
