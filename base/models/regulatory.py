from base.modules.regulatory import agency_registry
import os
from django.core.exceptions import ValidationError
from django.db import models
import datetime
import magic

from django.db import models, transaction


from .base import (
    BaseModelMixin,
)


class AccreditationDocument(BaseModelMixin):
    """
    Supporting an official Accreditation .
    """
    accreditation = models.ForeignKey(
        'Accreditation',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='accreditation_documents/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="accreditation document"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Doc for {self.accreditation.code}: {self.original_name}"


class Accreditation(BaseModelMixin):

    ACCREDITATION_TYPE_CHOICES = [
        ("Institutional", "Institutional"),
        ("Programme",      "Programme"),
        ("Specialized",    "Specialized"),
    ]

    STATUS_CHOICES = [
        ("Active",      "Active"),
        ("Pending",     "Pending"),
        ("Review",      "In Review"),
        ("Conditional", "Conditional"),
        ("Expired",     "Expired"),
    ]

    # Left blank for institution-wide accreditations (e.g. the CUE charter
    # itself), which don't belong to a single programme.
    programme = models.ForeignKey(
        'Programme',
        on_delete=models.CASCADE,
        related_name='accreditations',
        null=True,
        blank=True
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    body = models.CharField(
        max_length=30,
        choices=agency_registry.choices,
        help_text="e.g. CUE, KASNEB, Nursing Council of Kenya, Engineers Board of Kenya"
    )

    accreditation_type = models.CharField(
        max_length=20,
        choices=ACCREDITATION_TYPE_CHOICES,
        default="Programme"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    valid_from = models.DateField()
    valid_to = models.DateField(null=True)

    description = models.TextField(blank=True, default="")

    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['valid_to']

    def __str__(self):
        return f"{self.code} — {self.name}"

    def clean(self):
        super().clean()
        backend = agency_registry.get(self.body)
        if backend and self.status == "Active":
            result = backend.validate_accreditation(self)
            if not result.valid:
                raise ValidationError(result.errors)

    @property
    def is_expiring_soon(self):
        backend = agency_registry.get(self.body)
        lead_time = backend.renewal_lead_time_days() if backend else 180
        delta = (self.valid_to - datetime.date.today()).days
        return 0 <= delta <= lead_time

    @classmethod
    def expiring_within(cls, days=None):
        """
        days=None → use each accreditation's own body-specific lead time
        instead of one fixed window for every agency.
        """
        today = datetime.date.today()
        qs = cls.objects.filter(status="Active", valid_to__gte=today)
        if days is not None:
            cutoff = today + datetime.timedelta(days=days)
            return qs.filter(valid_to__lte=cutoff)
        return [a for a in qs if a.is_expiring_soon]


class RegistrationWindow(BaseModelMixin):
    window_choices = [
        ("course_registration", "Course Registration"),
        ("bursary", "Bursary/Financial Aid Registration"),
        ("hostel", "Hostel Allocation"),
        ("exam_registration", "Exam Registration"),
        ("backlog_exam", "Backlog/Supplementary Exam Registration"),
        ("graduation_candidacy", "Graduation Candidacy Nomination"),
        ("club_membership", "Club Membership Drive"),
        ("scholarship", "Scholarship Application"),
    ]

    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="registration_windows",
        help_text="e.g. Semester 2 2026/2027",
    )
    window_type = models.CharField(
        max_length=30,
        choices=window_choices,
        help_text="What this window governs, e.g. course registration, bursary",
    )
    programme = models.ForeignKey(
        "Programme",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="registration_windows",
        help_text="Optional: restrict this window to one program. Leave blank for institution-wide.",
    )
    opens_date = models.DateField()
    closes_date = models.DateField()
    late_closes_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional grace/late period end date, if late registration is allowed (often with a penalty fee).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Manual kill-switch to close a window early regardless of dates.",
    )

    class Meta:
        ordering = ["-opens_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "window_type", "programme"],
                name="unique_window_per_session_type_program",
            )
        ]

    def __str__(self):
        scope = f" - {self.programme}" if self.programme_id else ""
        return f"{self.get_window_type_display()} ({self.session}){scope}"

    @property
    def is_open(self):
        from django.utils import timezone
        today = timezone.now().date()
        end = self.late_closes_date or self.closes_date
        return self.is_active and self.opens_date <= today <= end

    @property
    def is_late_period(self):
        from django.utils import timezone
        today = timezone.now().date()
        return bool(
            self.late_closes_date
            and self.closes_date < today <= self.late_closes_date
        )


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


SOURCE_TYPE_CHOICES = [
    ("accreditation_expiry", "Accreditation Expiry"),
    ("report_deadline", "Report Deadline"),
    ("registration_window", "Registration Window"),
]

RECURRENCE_CHOICES = [
    ("none", "None"),
    ("semester", "Semester"),
    ("annual", "Annual"),
]


class ComplianceCalendarEvent(BaseModelMixin):
    """
    A denormalized projection over Accreditation, RegulatoryReport, and
    RegistrationWindow deadlines, so the calendar view can query one table
    instead of joining three. Regenerate via a management command / signal
    whenever a source record's date fields change — don't hand-maintain.
    """

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPE_CHOICES
    )

    # Generic-ish pointer without full GenericForeignKey overhead; app-level
    # code resolves source_id against the right model based on source_type.
    source_id = models.CharField(max_length=30, )

    title = models.CharField(max_length=255)
    due_date = models.DateField(db_index=True)

    recurrence = models.CharField(
        max_length=20,
        choices=RECURRENCE_CHOICES,
        default="none"
    )

    class Meta:
        ordering = ["due_date"]
        indexes = [
            models.Index(fields=["source_type", "source_id"])
        ]

    def __str__(self):
        return f"{self.title} ({self.due_date})"

    def days_remaining(self):
        from django.utils import timezone
        return (self.due_date - timezone.now().date()).days
