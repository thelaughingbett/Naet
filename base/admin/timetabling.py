from django.contrib import admin

from .mixins import BaseAdmin
from base.models import (
    Timetable,
    ExamClash,
    ExamSession,
    ExamVenue,
    Venue
)


@admin.register(Timetable)
class TimetableAdmin(BaseAdmin):
    pass


@admin.register(ExamClash)
class ExamClashAdmin(BaseAdmin):
    pass


@admin.register(ExamSession)
class ExamSessionAdmin(BaseAdmin):
    pass


@admin.register(ExamVenue)
class ExamVenueAdmin(BaseAdmin):
    pass


@admin.register(Venue)
class VenueAdmin(BaseAdmin):
    pass
