from django.urls import include, path
from staffConsole.views import ComingSoonView

urlpatterns = [
    path('lecturer/', include('staffConsole.urls.lecturer')),
    path('hod/', include('staffConsole.urls.hod')),

    path(
        'coming-soon',
        ComingSoonView.as_view(),
        name='coming-soon'
    )
]
