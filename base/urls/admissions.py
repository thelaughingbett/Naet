from django.urls import path

from base.views import ReportingView, DefermentView, HostelBookingView

urlpatterns = [
    path('reporting/', ReportingView.as_view(),     name='base-reporting'),
    path('defer/',     DefermentView.as_view(),      name='base-defer'),
    path('hostel/',    HostelBookingView.as_view(),  name='base-hostel-booking'),
]
