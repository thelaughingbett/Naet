from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from staffConsole.views import ComingSoonView
from base.views import ErrorNotFound
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('base.urls')),
    path('staff/', include('staffConsole.urls')),

    path(
        'coming-soon',
        ComingSoonView.as_view(),
        name='coming-soon'
    ),
    re_path(r'^(?P<resource>.*)/$', ErrorNotFound.as_view()),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
