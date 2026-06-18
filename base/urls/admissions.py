from django.urls import path

from base.views import ReportingView, DefermentView, HostelBookingView, ExamCardView, HostelGuideView

urlpatterns = [
    path('reporting/', ReportingView.as_view(),     name='base-reporting'),
    path('defer/',     DefermentView.as_view(),      name='base-defer'),
    path('hostel/',    HostelBookingView.as_view(),  name='base-hostel-booking'),
    path('exam-card/', ExamCardView.as_view(), name='base-exam-card'),
    path('hostel-guide', HostelGuideView.as_view(), name='base-hostel-guide')
]
