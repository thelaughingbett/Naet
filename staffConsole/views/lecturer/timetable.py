# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

import json

from django.shortcuts import render
from django.utils import timezone
from django.views import View

from base.models import ExamInvigilatorAssignment, Session, Timetable
from staffConsole.views.base import RoleRequiredMixin

# ── constants ─────────────────────────────────────────────────────────────────

DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI']

# Maps a 0-based index to a CSS color class.
# Assigned per unique course_code so the same course is always the same colour.
COLORS = ['color-1', 'color-2', 'color-3', 'color-4', 'color-5']


def _color_for_code(code: str, color_map: dict) -> str:
    """Return a stable color class for a course code, cycling through COLORS."""
    if code not in color_map:
        color_map[code] = COLORS[len(color_map) % len(COLORS)]
    return color_map[code]


def _class_names(curriculum) -> str:
    """
    Comma-joined class names for a (possibly shared) curriculum slot.
    Curriculum has no single Tclass anymore — `classes` is an M2M, and
    a shared lecture can legitimately serve several classes at once.
    The JS side only ever displays this as a flat string, so joining
    here keeps grid_rows_json/exam_list_json — and the JS that reads
    them — unchanged.
    """
    return ", ".join(c.class_name for c in curriculum.classes.all())


class MyTimetableView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/lecturer/my_timetable.html'

    def get(self, request):
        lecturer = self.get_profile()
        session = Session.objects.filter(is_active=True).first()

        # ── recurring lecture/lab slots ───────────────────────────────────
        # syllabus__course -> course (direct FK again); Tclass -> classes
        # (M2M, prefetched instead of select_related since it's a
        # multi-valued relation).
        lecture_slots = (
            Timetable.objects
            .filter(
                curriculum__professor=lecturer,
                curriculum__session=session,
            )
            .select_related(
                'curriculum__course',
                'venue',
            )
            .prefetch_related('curriculum__classes')
            .order_by('day', 'time_slot')
            if session else []
        )

        # ── exam / invigilation duties ────────────────────────────────────
        exam_duties = (
            ExamInvigilatorAssignment.objects
            .filter(
                lecturer=lecturer,
                exam_venue__exam_session__curriculum__session=session,
            )
            .select_related(
                'exam_venue__exam_session__curriculum__course',
                'exam_venue__venue',
                'exam_venue__exam_session',
            )
            .prefetch_related('exam_venue__exam_session__curriculum__classes')
            if session else []
        )

        # ── build grid data structure for the template ────────────────────
        # grid[day_code][time_slot] = slot_dict | None
        # We collect every unique time_slot that appears so the template
        # knows which rows to render.
        color_map: dict[str, str] = {}
        grid: dict[str, dict[str, dict]] = {day: {} for day in DAYS}
        time_slots_seen: set[str] = set()

        for slot in lecture_slots:
            day = slot.day
            time = slot.time_slot
            time_slots_seen.add(time)

            code = slot.curriculum.course.course_code
            color = _color_for_code(code, color_map)

            grid[day][time] = {
                'type':          'lecture',
                'code':          code,
                'name':          slot.curriculum.course.course_name,
                'venue':         slot.venue.venue_name,
                'class_name':    _class_names(slot.curriculum),
                'color':         color,
                'tag':           'Lecture',
                'tag_class':     'tag',
                'slot_id':       str(slot.record_id),
                'curriculum_id': str(slot.curriculum.record_id),
            }

        # Exam duties are date-specific; store them keyed by date so the
        # JS can highlight the correct column when rendering each week.
        exam_list = []

        for duty in exam_duties:
            es = duty.exam_venue.exam_session
            code = es.curriculum.course.course_code
            color = _color_for_code(code, color_map)

            exam_list.append({
                'date':          es.date.isoformat(),
                'time_slot':     es.time_slot,
                'code':          code,
                'name':          es.curriculum.course.course_name,
                'exam_type':     es.get_exam_type_display(),
                'venue':         duty.exam_venue.venue.venue_name,
                'class_name':    _class_names(es.curriculum),
                'color':         color,
                'tag':           'Invigilate',
                'tag_class':     'tag invig',
                'curriculum_id': str(es.curriculum.record_id),
            })
            time_slots_seen.add(es.time_slot)

        # Sort time slots chronologically (they're "HH:MM-HH:MM" strings)
        sorted_slots = sorted(time_slots_seen)

        # Collect the unique time_slots defined in Timetable.TIME_SLOTS
        # so we can provide human-readable labels.
        # Fall back to the raw string if not found.
        time_slot_labels = dict(Timetable.TIME_SLOTS)

        # Build the serialisable grid for the template / JS
        grid_rows = []
        for time in sorted_slots:
            label = time_slot_labels.get(time, time)
            row = {'time': time, 'label': label, 'days': {}}
            for day in DAYS:
                row['days'][day] = grid[day].get(time)   # None if empty
            grid_rows.append(row)

        # Serialise grid_rows for JS
        grid_rows_js = [
            {'time': r['time'], 'label': r['label'],
             'days': {day: r['days'][day] for day in DAYS}}
            for r in grid_rows
        ]

        context = {
            **self.get_context_data(),
            'session':          session,
            'lecturer':         lecturer,
            'grid_rows':        grid_rows,
            'days':             DAYS,
            'grid_rows_json':   json.dumps(grid_rows_js),
            'exam_list_json':   json.dumps(exam_list),
            'today_day':        timezone.now().strftime('%a').upper()[:3],
        }
        return render(request, self.template_name, context)
