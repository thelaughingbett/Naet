from django.urls import path

from base.views import CurriculumView, UnitRegistrationView, ResultsView, DropElectiveUnitView

urlpatterns = [
    path('curriculum/', CurriculumView.as_view(),       name='base-curriculum'),
    path('units/',      UnitRegistrationView.as_view(),
         name='base-unit-registration'),
    path('units/drop/', DropElectiveUnitView.as_view(),
         name='drop-elective-unit'),
    path('results/',    ResultsView.as_view(),           name='base-results'),
]
