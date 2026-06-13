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


from http import HTTPStatus

from decouple import config

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.db import (
    DatabaseError,
    IntegrityError,
    transaction
)
from django.utils.http import url_has_allowed_host_and_scheme


from base.forms import (
    LoginForm,
)
from .base import StudentContextMixin, StudentProfileRequiredMixin


class LoginView(
    View
):
    def get(self, request):
        form = LoginForm()
        context = {
            'form': form
        }
        return render(request, 'base/login.html', context)

    def post(self, request):
        form = LoginForm(request.POST)

        next_url = request.GET.get('next') or request.POST.get('next') or '/'

        is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            # require_https=request.is_secure() if not settings.DEBUG else '',
        )

        if form.is_valid() and is_safe:
            email = form.cleaned_data['emaile']
            password = form.cleaned_data['password']
            try:
                user = authenticate(request, username=email, password=password)
                login(request, user)
                return redirect(next_url)
            except:
                return HttpResponse('failed to login')

        return HttpResponse('error response')


class LogoutView(View):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def post(self, request):
        logout(request)
        return redirect(reverse('base-login'))


class SettingsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config('LOGIN_URL') + '?next=settings'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        context = {

        }
        return render(request, 'base/settings.html', context)
