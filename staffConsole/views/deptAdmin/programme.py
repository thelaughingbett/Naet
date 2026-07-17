# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import json

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import Programme, Tclass
from staffConsole.views.base import RoleRequiredMixin


def _serialize(programme: Programme) -> dict:
    return {
        'id':             str(programme.record_id),
        'code':           programme.code or '',
        'name':           programme.programme_name,
        'degree_type':    programme.degree_type,
        'duration_years': programme.duration_years,
        'duration':       f"{programme.duration_years} Year{'s' if programme.duration_years != 1 else ''}",
        'level':          programme.level,
        'status':         programme.status,
        'description':    programme.description,
    }


class ProgrammeListView(RoleRequiredMixin, View):
    required_role = 'deptadmin'
    template_name = 'staff/dept_admin/programmes.html'

    def get(self, request):
        admin = self.get_profile()
        dept = admin.department

        programmes = (
            Programme.objects
            .filter(department=dept)
            .order_by('programme_name')
        )
        rows = [_serialize(p) for p in programmes]
        total = len(rows)
        active = sum(1 for r in rows if r['status'] == 'Active')

        context = {
            **self.get_context_data(),
            'department':      dept,
            'programmes_json': json.dumps(rows),
            'stat_total':       total,
            'stat_active':      active,
            'stat_inactive':    total - active,
            'degree_choices':   Programme.kenyan_degrees,
            'level_choices':    Programme.LEVEL_CHOICES,
        }
        return render(request, self.template_name, context)


class ProgrammeSaveAjaxView(RoleRequiredMixin, View):
    """
    POST /dept-admin/programmes/save/
    Body JSON: { id (optional), code, name, degree_type, duration_years,
                 level, status, description }
    Creates a Programme when id is absent/blank; updates otherwise.
    Scoped to the admin's own department — you cannot create or edit
    a programme in another department through this endpoint.
    """
    required_role = 'deptadmin'

    def post(self, request):
        admin = self.get_profile()
        dept = admin.department

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Bad payload'}, status=400)

        prog_id = (data.get('id') or '').strip()
        code = (data.get('code') or '').strip()
        name = (data.get('name') or '').strip()
        degree_type = data.get('degree_type', '')
        duration_years = data.get('duration_years')
        level = data.get('level', 'Undergraduate')
        status = data.get('status', 'Active')
        description = data.get('description', '')

        if not name or not degree_type or not duration_years:
            return JsonResponse(
                {'error': 'Name, degree type, and duration are required.'}, status=400
            )

        try:
            duration_years = int(duration_years)
            if duration_years <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return JsonResponse(
                {'error': 'Duration must be a positive number of years.'}, status=400
            )

        valid_degrees = {d[0] for d in Programme.kenyan_degrees}
        if degree_type not in valid_degrees:
            return JsonResponse({'error': f'Invalid degree type: {degree_type}'}, status=400)

        valid_levels = {l[0] for l in Programme.LEVEL_CHOICES}
        if level not in valid_levels:
            return JsonResponse({'error': f'Invalid level: {level}'}, status=400)

        valid_statuses = {s[0] for s in Programme.STATUS_CHOICES}
        if status not in valid_statuses:
            return JsonResponse({'error': f'Invalid status: {status}'}, status=400)

        try:
            if prog_id:
                try:
                    programme = Programme.objects.get(
                        record_id=prog_id, department=dept)
                except Programme.DoesNotExist:
                    return JsonResponse({'error': 'Programme not found'}, status=404)

                programme.code = code or None
                programme.programme_name = name
                programme.degree_type = degree_type
                programme.duration_years = duration_years
                programme.level = level
                programme.status = status
                programme.description = description
                programme.save()
                created = False
            else:
                programme = Programme.objects.create(
                    department=dept,
                    code=code or None,
                    programme_name=name,
                    degree_type=degree_type,
                    duration_years=duration_years,
                    level=level,
                    status=status,
                    description=description,
                )
                created = True
        except IntegrityError:
            return JsonResponse(
                {'error': f'Programme code "{code}" is already in use.'}, status=400
            )

        return JsonResponse({
            'status':    'created' if created else 'updated',
            'programme': _serialize(programme),
        })


class ProgrammeDeleteAjaxView(RoleRequiredMixin, View):
    """
    DELETE /dept-admin/programmes/<uuid:programme_id>/delete/

    Tclass.programme is on_delete=PROTECT, so a programme with any
    class attached cannot actually be deleted — we surface that as a
    clear error rather than letting ProtectedError bubble up as a 500.
    """
    required_role = 'deptadmin'

    def delete(self, request, programme_id):
        admin = self.get_profile()
        dept = admin.department

        try:
            programme = Programme.objects.get(
                record_id=programme_id, department=dept)
        except Programme.DoesNotExist:
            return JsonResponse({'error': 'Programme not found'}, status=404)

        try:
            programme.delete()
        except ProtectedError:
            class_count = Tclass.objects.filter(
                programme_id=programme_id).count()
            return JsonResponse({
                'error': (
                    f'Cannot delete "{programme.programme_name}" — it has '
                    f'{class_count} class{"es" if class_count != 1 else ""} attached. '
                    f'Set its status to Inactive instead.'
                )
            }, status=400)

        return JsonResponse({'status': 'deleted'})
