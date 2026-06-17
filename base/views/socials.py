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

import datetime

from django.contrib import messages

from http import HTTPStatus

from decouple import config

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

from django.db import (
    models
)
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Q

from base.models import (
    NewsItem,
    EventItem
)
from .base import (
    StudentProfileRequiredMixin,
    StudentContextMixin
)

from base.modules.socials.news.registry import news_registry
from base.modules.socials.events.registry import events_registry


class EventsView(LoginRequiredMixin, StudentProfileRequiredMixin, View):
    login_url = config("LOGIN_URL") + '?next=socials/events/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        category = request.GET.get('category', '')
        date_from = request.GET.get('date_from', '')
        search = request.GET.get('search', '')

        # --- Mode A: model-backed (preferred — sync already happened) ---
        if EventItem.objects.exists():
            events = EventItem.objects.filter(is_published=True)

            if category:
                events = events.filter(category__iexact=category)
            if date_from:
                events = events.filter(date__gte=date_from)
            if search:
                events = events.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(location__icontains=search)
                )

            categories = (
                EventItem.objects
                .filter(is_published=True)
                .values_list('category', flat=True)
                .distinct()
                .order_by('category')
            )

            return render(request, 'base/socials/events.html', {
                'events':     events,
                'categories': categories,
                'category':   category,
                'date_from':  date_from,
                'search':     search,
                'mode':       'model',
            })

        # --- Mode B: no model data yet, fetch live from backends ---
        events = []
        categories = set()

        date_from_obj = None
        if date_from:
            try:
                date_from_obj = datetime.date.fromisoformat(date_from)
            except ValueError:
                pass

        for name, backend in events_registry.all().items():
            result = backend.fetch(limit=50, upcoming_only=True)
            if not result.success:
                continue

            for event in result.events:
                categories.add(event.category)

                if category and event.category.lower() != category.lower():
                    continue
                if date_from_obj and event.date < date_from_obj:
                    continue
                if search:
                    haystack = f"{event.title} {event.description} {event.location or ''}".lower(
                    )
                    if search.lower() not in haystack:
                        continue

                events.append(event)

        events.sort(key=lambda e: (e.date, e.start_time or datetime.time.min))

        return render(request, 'base/socials/events.html', {
            'events':     events,
            'categories': sorted(categories),
            'category':   category,
            'date_from':  date_from,
            'search':     search,
            'mode':       'live',
        })


class NewsView(LoginRequiredMixin, StudentProfileRequiredMixin, View):
    login_url = config("LOGIN_URL") + '?next=socials/news/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        category = request.GET.get('category', '')
        search = request.GET.get('search', '')

        # --- Mode A: model-backed (preferred — sync already happened via Celery) ---
        if NewsItem.objects.exists():
            articles = NewsItem.objects.filter(is_published=True)

            if category:
                articles = articles.filter(category__iexact=category)
            if search:
                articles = articles.filter(
                    models.Q(title__icontains=search) |
                    models.Q(summary__icontains=search)
                )

            # pull distinct categories for the filter dropdown
            categories = (
                NewsItem.objects
                .filter(is_published=True)
                .values_list('category', flat=True)
                .distinct()
                .order_by('category')
            )

            return render(request, 'base/socials/news.html', {
                'articles':   articles,
                'categories': categories,
                'category':   category,
                'search':     search,
                'mode':       'model',
            })

        # --- Mode B: no model data, fetch live from backends ---
        articles = []
        categories = set()

        for name, backend in news_registry.all().items():
            result = backend.fetch(limit=20)
            if result.success:
                for article in result.articles:
                    categories.add(article.category)

                    # apply filters manually
                    if category and article.category.lower() != category.lower():
                        continue
                    if search and search.lower() not in (
                        article.title.lower() + article.summary.lower()
                    ):
                        continue

                    articles.append(article)

        # sort by date desc
        articles.sort(key=lambda a: a.date, reverse=True)

        return render(request, 'base/socials/news.html', {
            'articles':   articles,
            'categories': sorted(categories),
            'category':   category,
            'search':     search,
            'mode':       'live',
        })
