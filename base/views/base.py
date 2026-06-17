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

from ..models import (
    Student,
    Session,
)


# TODO : make this a singleton
logger = logging.getLogger(__name__)


class StudentContextMixin:
    """Adds student + session to context automatically"""

    def get_student(self, request):
        # TODO : get from cache
        try:
            return Student.objects.select_related(
                'class_entered__programme__department__school'
            ).get(user=request.user)
        except Student.DoesNotExist:
            return None

    def get_active_session(self):
        try:
            # TODO :  get session from student programme
            return Session.objects.get(is_active=True)
        except Session.DoesNotExist:
            return None


class StudentProfileRequiredMixin:
    """Checks if the user has a student profile before letting them view the page."""

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(request.user, 'student_profile'):
            # Stop the user and show an error page
            return redirect('/admin')
            raise PermissionDenied("You do not have a student profile.")

        return super().dispatch(request, *args, **kwargs)
