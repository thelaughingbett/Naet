from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from staffConsole.views import ComingSoonView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('base.urls')),
    path('staff/', include('staffConsole.urls')),

    path(
        'coming-soon',
        ComingSoonView.as_view(),
        name='coming-soon'
    )
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
