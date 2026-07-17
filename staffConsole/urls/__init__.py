from django.urls import include, path


urlpatterns = [
    path('lecturer/', include('staffConsole.urls.lecturer'))
]
