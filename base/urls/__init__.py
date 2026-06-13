# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.urls import include, path

from base.views import ping

urlpatterns = [
    path('ping/', ping, name='ping'),

    path('',          include('base.urls.auth')),
    path('',          include('base.urls.dashboard')),
    path('socials/',  include('base.urls.socials')),
    path('academics/', include('base.urls.academics')),
    path('admissions/', include('base.urls.admissions')),
    path('financials/', include('base.urls.financials')),
    path('timetable/', include('base.urls.timetable')),
    path('evaluations/', include('base.urls.evaluations')),

    # 404-not-found
    # path('<path:unmatched_path>', views.catch_all_view, name='catch_all'),
]
