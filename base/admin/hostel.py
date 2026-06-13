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
    Hostel,
    HostelAllocation,
    HostelWarden,
    ResidentStudent,
    Room,
)


@admin.register(Hostel)
class HostelAdmin(BaseAdmin):
    pass


@admin.register(Room)
class RoomAdmin(BaseAdmin):
    pass


@admin.register(HostelAllocation)
class HostelAllocationAdmin(BaseAdmin):
    pass


@admin.register(HostelWarden)
class HostelWardenAdmin(BaseAdmin):
    pass


@admin.register(ResidentStudent)
class ResidentStudentAdmin(BaseAdmin):
    pass
