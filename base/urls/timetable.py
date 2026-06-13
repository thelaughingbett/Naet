from django.urls import path

from base.views import WeeklyScheduleView, ExamTimetableView

urlpatterns = [
    path('schedule/', WeeklyScheduleView.as_view(),  name='base-weekly-schedule'),
    path('exams/',    ExamTimetableView.as_view(),    name='base-exam-timetable'),
]
