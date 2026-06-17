from django.urls import path

from base.views import (
    LoginView,
    LogoutView,
    RegisterView,
    RegistrationSucessView,
    HostelBookingRegistrationView,
    SettingsView,
    DataExportView
)

urlpatterns = [
    path('login/',    LoginView.as_view(),  name='base-login'),
    path('logout/',   LogoutView.as_view(), name='base-logout'),
    path('register/', RegisterView.as_view(), name='base-register'),
    path('registration-sucess', RegistrationSucessView.as_view(),
         name='base-registration-sucess'),
    path('registration-hostel-booking', HostelBookingRegistrationView.as_view(),
         name='base-registration-hostel-booking'),
    path('settings/', SettingsView.as_view(), name='base-settings'),
    path('settings/export', DataExportView.as_view(), name='data-export')
]
