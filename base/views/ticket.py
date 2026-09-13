# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
NOTE ON PLACEMENT: I don't know your actual views/ folder structure —
document 23 showed ReportingView/DefermentView/HostelBookingView/
ExamCardView/HostelGuideView all living together in what looked like
one admissions-focused module. "Raise a Ticket" belongs to Support &
Grievances per the sidebar (document 21), not admissions, so I've
written this as its own file — but if your project keeps everything
in one views module, just paste this class in there instead.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views import View

from decouple import config

from base.models import Complaint, ComplaintDocument
from .base import StudentProfileRequiredMixin, StudentContextMixin

TICKETS_PER_PAGE = 4

# Not enforced anywhere on ComplaintDocument itself — the model's TODO
# comment flags wanting a size cap "e.g. 25mbs" but never implements
# one. Enforced here at the view level instead, same pattern as
# DefermentView's 5MB cap on deferment documents. If you'd rather this
# live on the model (so ANY upload path gets it, not just this view),
# say so and I'll move it into ComplaintDocument.clean().
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


class TicketView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """
    Student-facing ticket/grievance portal — "Raise a Ticket" under
    Support & Grievances. Lists the student's own Complaint records
    with stats and a category breakdown, and lets them file a new one
    with optional attachments.

    Deliberately does NOT expose any way for a student to mark their
    own ticket Resolved — Complaint.clean() requires resolution_remarks,
    and per the escalation workflow, resolution is a staff/HOD/Dean
    action, not a student self-service one.
    """

    template_name = 'base/support/raise_ticket.html'
    login_url = config("LOGIN_URL") + '?next=support/raise-ticket/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def _get_stats(self, queryset):
        return {
            'total': queryset.count(),
            'open': queryset.filter(status='Open').count(),
            'in_progress': queryset.filter(status='In_Progress').count(),
            'resolved': queryset.filter(status='Resolved').count(),
        }

    def _get_category_breakdown(self, queryset, category_choices):
        total = queryset.count() or 1
        counts = dict(
            queryset.values_list('category').annotate(c=Count('record_id'))
        )
        return [
            {
                'value': value,
                'label': label,
                'count': counts.get(value, 0),
                'percent': round(counts.get(value, 0) / total * 100, 1),
            }
            for value, label in category_choices
        ]

    def get(self, request):
        student = self.get_student(request)

        category_choices = Complaint._meta.get_field('category').choices
        priority_choices = Complaint._meta.get_field('priority').choices

        queryset = Complaint.objects.filter(
            student=student
        ).select_related().prefetch_related(
            'documents', 'escalation_history'
        ).order_by('-date_opened')

        stats = self._get_stats(queryset)
        category_breakdown = self._get_category_breakdown(
            queryset, category_choices
        )

        paginator = Paginator(queryset, TICKETS_PER_PAGE)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context = {
            'student': student,
            'page_obj': page_obj,
            'stats': stats,
            'category_breakdown': category_breakdown,
            'category_choices': category_choices,
            'priority_choices': priority_choices,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        student = self.get_student(request)

        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category')
        priority = request.POST.get('priority')
        description = request.POST.get('description', '').strip()
        files = request.FILES.getlist('documents')

        if not subject or not category or not description:
            messages.error(request, "Please fill in all required fields.")
            return redirect('base-ticket')

        for f in files:
            if f.size > MAX_ATTACHMENT_SIZE:
                messages.error(
                    request,
                    f'File "{f.name}" exceeds the '
                    f'{MAX_ATTACHMENT_SIZE // (1024 * 1024)} MB limit.'
                )
                return redirect('base-ticket')

        try:
            with transaction.atomic():
                complaint = Complaint(
                    student=student,
                    category=category,
                    priority=priority or 'Medium',
                    subject=subject,
                    description=description,
                )
                complaint.full_clean()
                complaint.save()

                for f in files:
                    doc = ComplaintDocument(
                        complaint=complaint,
                        file=f,
                        uploaded_by_role='student',
                        uploaded_by_user=request.user,
                    )
                    doc.full_clean()
                    doc.save()
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages)
                           if hasattr(e, 'messages') else str(e))
            return redirect('base-ticket')

        messages.success(request, "Your ticket has been submitted.")
        return redirect('base-ticket')
