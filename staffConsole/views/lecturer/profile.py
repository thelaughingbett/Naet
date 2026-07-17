# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import Lecturer
from staffConsole.views.base import RoleRequiredMixin


class LecturerProfileDetailView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/profile_details.html'

    def get(self, request):
        lecturer = self.get_profile()

        context = {
            **self.get_context_data(),
            'lecturer':       lecturer,
            'title_choices':  Lecturer.academic_titles_abbreviated,
        }
        return render(request, self.template_name, context)


class LecturerProfileUpdateAjaxView(RoleRequiredMixin, View):
    """
    POST /lecturer/profile/update/
    Body JSON: {
        first_name, last_name,           # → User
        title, phone_number, alternative_phone,
        office_location, office_hours,
        personal_email, bio, research_interests,   # → Lecturer
    }
    Only updates fields that are actually present in the payload —
    omitted keys are left untouched rather than cleared.
    """
    required_role = 'lecturer'

    def post(self, request):
        lecturer = self.get_profile()
        user = lecturer.user

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Bad payload'}, status=400)

        valid_titles = {t[0] for t in Lecturer.academic_titles_abbreviated}
        if 'title' in data and data['title'] not in valid_titles:
            return JsonResponse({'error': f'Invalid title: {data["title"]}'}, status=400)

        # ── User fields ──────────────────────────────────────────────
        user_fields = ('first_name', 'last_name')
        for field in user_fields:
            if field in data:
                setattr(user, field, (data[field] or '').strip() or None)
        if any(f in data for f in user_fields):
            user.save(update_fields=[f for f in user_fields if f in data])

        # ── Lecturer fields ──────────────────────────────────────────
        lecturer_fields = (
            'title', 'phone_number', 'alternative_phone',
            'office_location', 'office_hours',
            'personal_email', 'bio', 'research_interests',
        )
        touched = []
        for field in lecturer_fields:
            if field in data:
                setattr(lecturer, field, (data[field] or '').strip() or None)
                touched.append(field)
        if touched:
            lecturer.save(update_fields=touched)

        return JsonResponse({
            'status': 'updated',
            'full_name': user.full_name,
            'title_display': lecturer.get_title_display(),
        })
