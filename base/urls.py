from . import views
from django.urls import path
from .views import (
    CourseEvaluationView,
    CurriculumView,
    DefermentView,
    EventsView,
    ExamTimetableView,
    FeeStatementView,
    HostelBookingView,
    HostelEvaluationView,
    LecturerEvaluationView,
    NewsView,
    RegisterView,
    ReportingView,
    ResultsView,
    IndexView,
    LogoutView,
    LoginView,
    UnitRegistrationView,
    WeeklyScheduleView,
    PaymentView,
    SettingsView
)

urlpatterns = [
    # auth
    path(
        'login/',
        LoginView.as_view(),
        name='base-login'
    ),
    path(
        'logout/',
        LogoutView.as_view(),
        name='base-logout'
    ),
    path(
        'register/',
        RegisterView.as_view(),
        name='base-register'
    ),
    path(
        'settings/',
        SettingsView.as_view(),
        name='base-settings'
    ),

    # Dashboard
    path(
        '',
        IndexView.as_view(),
        name='base-index'
    ),

    # socials
    path(
        'socials/events/',
        EventsView.as_view(),
        name='base-events'
    ),
    path(
        'socials/news/',
        NewsView.as_view(),
        name='base-news'
    ),

    # academics
    path(
        'academics/curriculum/',
        CurriculumView.as_view(),
        name='base-curriculum'
    ),
    path(
        'academics/units/',
        UnitRegistrationView.as_view(),
        name='base-unit-registration'
    ),
    path(
        'academics/results/',
        ResultsView.as_view(),
        name='base-results'
    ),

    # admissions
    path(
        'admissions/reporting/',
        ReportingView.as_view(),
        name='base-reporting'
    ),
    path(
        'admissions/defer/',
        DefermentView.as_view(),
        name='base-defer'
    ),
    path(
        'admissions/hostel/',
        HostelBookingView.as_view(),
        name='base-hostel-booking'
    ),

    # financials
    path(
        'financials/fees/',
        FeeStatementView.as_view(),
        name='base-fee-statement'
    ),
    path(
        'financials/fees/pay/',
        PaymentView.as_view(),
        name='base-payment'
    ),

    # timetable
    path(
        'timetable/schedule/',
        WeeklyScheduleView.as_view(),
        name='base-weekly-schedule'
    ),
    path(
        'timetable/exams/',
        ExamTimetableView.as_view(),
        name='base-exam-timetable'
    ),

    # evaluations
    path(
        'evaluations/course/',
        CourseEvaluationView.as_view(),
        name='base-course-evaluation'
    ),
    path(
        'evaluations/lecturer/',
        LecturerEvaluationView.as_view(),
        name='base-lecturer-evaluation'
    ),
    path(
        'evaluations/hostel/',
        HostelEvaluationView.as_view(),
        name='base-hostel-evaluation'
    ),

]
