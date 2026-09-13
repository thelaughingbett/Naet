from django.urls import path

from base.views import WeeklyScheduleView, ExamTimetableView, execution_history, log_execution

urlpatterns = [
    path('schedule/', WeeklyScheduleView.as_view(),  name='base-weekly-schedule'),
    path('exams/',    ExamTimetableView.as_view(),    name='base-exam-timetable'),
    path(
        'timetable/execution-history/',
        execution_history,
        name='execution-history'
    ),
    path('timetable/log-execution/', log_execution, name='log-execution'),

]
