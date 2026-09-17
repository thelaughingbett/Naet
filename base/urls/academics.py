from django.urls import path

from base.views import (CurriculumView, UnitRegistrationView, ResultsView, DropElectiveUnitView,
                        result_challenge_history, submit_result_challenge,    requisition_history, submit_requisition)

urlpatterns = [
    path(
        'curriculum/',
        CurriculumView.as_view(),
        name='base-curriculum'
    ),
    path(
        'units/',
        UnitRegistrationView.as_view(),
        name='base-unit-registration'
    ),
    path(
        'units/drop/',
        DropElectiveUnitView.as_view(),
        name='drop-elective-unit'
    ),
    path(
        'results/',
        ResultsView.as_view(),
        name='base-results'
    ),
    path(
        'results/challenge-history/',
        result_challenge_history,
        name='result-challenge-history'
    ),
    path(
        'results/challenge/',
        submit_result_challenge,
        name='submit-result-challenge'
    ),
    path(
        'results/requisition-history/',
        requisition_history,
        name='requisition-history'
    ),
    path(
        'results/requisition/',
        submit_requisition,
        name='submit-requisition'
    ),
]
