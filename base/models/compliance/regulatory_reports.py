# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Regulatory reporting domain — statutory submissions to an agency
(enrolment returns, graduation audits, staff workload ledgers,
financial statements, etc.), the evidence files backing them, and the
recurring-report rollover from one session to the next.

Like accreditation.py, defers agency-specific rules (accepted document
types, submission validation) to whatever backend `agency_registry`
resolves `self.agency`/`self.report.agency` to, rather than hardcoding
one agency's requirements onto the model.

NOTE ON `STATUS_CHOICES`: this module-level name is fairly generic —
worth being deliberate about it if it's ever imported by name
elsewhere (`from base.models.compliance.regulatory_reports import
STATUS_CHOICES`), since `Accreditation` in accreditation.py also
defines its own `STATUS_CHOICES` as a *class* attribute (a different,
non-colliding namespace, but easy to confuse at a glance). Left
unrenamed here since it's a straight carry-over from the original
source, not a naming decision made during this split.
"""

import os
import datetime
import magic

from django.core.exceptions import ValidationError
from django.db import models, transaction

from base.modules.regulatory import agency_registry
from ..base import BaseModelMixin


# --- REGULATORY REPORTING LIST CHOICES ---
TRIGGER_CHOICES = [
    ("recurring",              "Recurring"),
    ("accreditation_renewal",  "Accreditation Renewal"),
    ("ad_hoc",                 "Ad Hoc"),
]

STATUS_CHOICES = [
    ("Draft",     "Draft"),
    ("Submitted", "Submitted"),
    ("Review",    "In Review"),
    ("Approved",  "Approved"),
    ("Rejected",  "Rejected"),
]

# --- 1. THE SUPPORTING DOCUMENT ATTACHMENT SYSTEM ---


class RegulatoryReportDocument(BaseModelMixin):
    """
    Supporting evidence uploaded alongside an official statutory report.
    Accepts data payloads, payment receipts, signatures, or error logs.
    """
    report = models.ForeignKey(
        'RegulatoryReport',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='regulatory_reports/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g., Signed transmittal memo, CSV data export dump"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_allowed_mime_types(self) -> dict:
        ALLOWED_MIME_TYPES = [

        ]
        backend = agency_registry.get(
            self.report.agency) if self.report_id else None
        if backend:
            return {ext: ALLOWED_MIME_TYPES.get(ext, []) for ext in backend.submission_document_types()}
        return self.allowed_mime_types  # fallback to the class default

    def clean(self):
        """
        Enforces security checks to protect server directories while 
        allowing data sheets, PDFs, and system logs.
        """
        super().clean()
        if self.file and self.report_id:
            backend = agency_registry.get(self.report.agency)
            allowed = backend.requirement.document_types if backend else [
                '.pdf', '.csv', '.xlsx']
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext not in allowed:
                raise ValidationError(
                    f"{self.report.agency} does not accept '{ext}' files.")

            # content sniffing: does the file actually contain what its name claims?
            self.file.seek(0)
            header = self.file.read(2048)
            self.file.seek(0)
            detected_mime = magic.from_buffer(header, mime=True)

            # if detected_mime not in ALLOWED_MIME_TYPES[ext]:
            #     raise ValidationError(
            #         f"File content does not match its extension. Detected '{detected_mime}' "
            #         f"for a file named with extension '{ext}'."
            #     )

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Doc for {self.report.code}: {self.original_name}"


# --- 2. THE MAIN REGULATORY REPORT CORE ---

REPORT_TYPE_CHOICES = [
    ("Enrolment_Return", "Annual Student Enrolment Return"),
    ("Graduation_Audit", "Graduation Performance Data Return"),
    ("Staff_Ledger", "Academic Staff Workload Return"),
    ("Financial_Statement", "Institutional Financial Audited Statement"),
    ("Accreditation_Self_Audit", "Program Self-Assessment Audit Report"),
    ("Other", "Other (Specify Custom Report Title Below)"),
]


class RegulatoryReport(BaseModelMixin):
    """
    Tracks state-level submissions, compliance timelines, and attached 
    evidence files for secondary administrative analysis.
    """
    related_accreditation = models.ForeignKey(
        'Accreditation',
        on_delete=models.SET_NULL,
        related_name='reports',
        null=True,
        blank=True
    )

    session = models.ForeignKey(
        'Session',
        on_delete=models.SET_NULL,
        related_name='regulatory_reports',
        null=True,
        blank=True
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    agency = models.CharField(
        max_length=30,
        choices=agency_registry.choices,   # callable, not a static list
    )  # consider  appending as viable agency other here and maybe a title for a report

    report_type = models.CharField(
        max_length=100,
        default="Enrolment_Return",
        db_index=True,
        help_text="Primary dropdown category selection mapping to standard reporting templates."
    )

    #  The Fallback Text Entry Field
    # Left blank by default. Activated only when a user selects 'Other'.
    custom_report_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Mandatory field if 'Other' is selected above. Type the distinct title here."
    )

    trigger_type = models.CharField(
        max_length=30,
        choices=TRIGGER_CHOICES,
        default="ad_hoc"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft"
    )

    description = models.TextField(blank=True, default="")
    due_date = models.DateField()
    submission_date = models.DateField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.code} — {self.name}"

    def clean(self):
        """
        CUE Statutory Hardstop: Blocks administrative staff from moving 
        a report to 'Submitted' status unless the physical tracking 
        evidence files are explicitly attached to the instance.
        """
        super().clean()

        # Extract standard database choices keys dynamically from the list tuple
        valid_dropdown_keys = [key for key, label in REPORT_TYPE_CHOICES]

        # Case 1: The user selected 'Other' from your dropdown interface list
        if self.report_type == "Other":
            if not self.custom_report_title or not self.custom_report_title.strip():
                raise ValidationError({
                    'custom_report_title': "Compliance Block: You selected 'Other' as the report type. "
                                           "Please provide a distinct custom report title."
                })

            # Formatting Optimization: Normalize text values to clean string representations
            self.custom_report_title = self.custom_report_title.strip()

        # Case 2: The user selected a standard template from the list option dropdown
        else:
            # Enforce that whatever string value is input matches our standard selection matrix keys
            if self.report_type not in valid_dropdown_keys:
                raise ValidationError({
                    'report_type': f"Validation Error: '{self.report_type}' is not a recognized report category type. "
                    f"Please choose an option from the list or select 'Other'."
                })

            # Data Integrity Cleanup: If they selected a standard option, wipe any accidental custom text field values
            self.custom_report_title = None

        # Note: If self.pk exists (instance is written), check that at least one file exists
        if self.pk and self.status == "Submitted":
            backend = agency_registry.get(self.agency)
            if backend:
                result = backend.validate_submission(self)
                if not result.valid:
                    raise ValidationError(result.errors)
            elif not self.documents.exists():
                # fallback for an agency with no registered backend yet
                raise ValidationError(
                    "Compliance Block: Cannot set status to 'Submitted' without "
                    "attaching the official signed transmittal file or data sheet."
                )

    def set_status(self, new_status):
        """
        Enforces execution patterns so timestamps lock in correctly.
        """
        self.status = new_status
        if new_status == "Submitted" and not self.submission_date:
            self.submission_date = datetime.date.today()

        # Trigger explicit clean check before updating fields inside transaction logs
        self.full_clean()
        self.save(update_fields=['status', 'submission_date'])

    @property
    def is_overdue(self):
        return self.status not in ("Submitted", "Approved") and self.due_date < datetime.date.today()

    @classmethod
    def rollover_for_session(cls, from_session, to_session):
        """
        Asynchronously handles database rollover operations safely across semesters.
        """
        with transaction.atomic():
            day_shift = (to_session.start_date - from_session.start_date).days
            created = []

            recurring_reports = cls.objects.filter(
                session=from_session,
                trigger_type="recurring"
            )

            for report in recurring_reports:
                new_report = cls.objects.create(
                    related_accreditation=report.related_accreditation,
                    session=to_session,
                    # Safe handling for unique naming constraints on new session keys
                    code=f"{report.code}-{to_session.academic_year.replace('/', '-')}-S{to_session.semester}",
                    name=report.name,
                    agency=report.agency,
                    trigger_type=report.trigger_type,
                    description=report.description,
                    due_date=report.due_date +
                    datetime.timedelta(days=day_shift),
                    status="Draft",
                    version=1
                )
                created.append(new_report)

            return created

    def __str__(self):
        # Intelligent String Representation output formatting
        if self.report_type == "Other":
            return f"{self.code} — {self.custom_report_title} (Custom Report)"
        return f"{self.code} — {self.get_report_type_label()}"

    def get_report_type_label(self):
        """Helper tool mirroring Django's native choice label resolution."""
        mapping = dict(REPORT_TYPE_CHOICES)
        return mapping.get(self.report_type, self.report_type)
