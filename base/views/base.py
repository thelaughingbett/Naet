# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging


from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


# TODO : make this a singleton
logger = logging.getLogger(__name__)


class StudentProfileRequiredMixin:
    """
    Ensures the authenticated user has a student profile before the view runs.

    LoginRequiredMixin (which should always appear before this in the MRO)
    handles unauthenticated users first — this mixin only ever fires for
    users who are already logged in but don't have a student profile
    (e.g. a lecturer who wanders onto a student URL).

    Behaviour:
      - Recognised staff role  →  redirect to their own dashboard so they
                                  land somewhere useful rather than a 403.
      - Authenticated but no recognisable role  →  PermissionDenied (403).
    """

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'student_profile'):
            from staffConsole.views.base import get_staff_dashboard_url
            dashboard = get_staff_dashboard_url(request.user)
            if dashboard and dashboard != '/':
                return redirect(dashboard)
            raise PermissionDenied(
                "This page is only accessible to students."
            )
        return super().dispatch(request, *args, **kwargs)


class StudentContextMixin:
    """
    Provides get_student() and get_active_session() helpers to any view
    that needs the current student and/or the active session.
    """

    def get_student(self, request):
        return getattr(request.user, 'student_profile', None)

    def get_active_session(self):
        from base.models import Session
        return Session.objects.filter(is_active=True).first()
