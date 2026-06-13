from django.urls import path

from base.views import CurriculumView, UnitRegistrationView, ResultsView

urlpatterns = [
    path('curriculum/', CurriculumView.as_view(),       name='base-curriculum'),
    path('units/',      UnitRegistrationView.as_view(), name='base-unit-registration'),
    path('results/',    ResultsView.as_view(),           name='base-results'),
]
