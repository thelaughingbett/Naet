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

"""
Innovation Office models
Covers: ideation, incubation, funding/grants, IP & patents, R&D projects,
events, and industry partnerships.
"""

from ..base import BaseModelMixin
from django.db import models


from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

# ---------------------------------------------------------------------------
# Ideation
# ---------------------------------------------------------------------------


class Idea(BaseModelMixin):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted to Startup"

    title = models.CharField(max_length=255)
    description = models.TextField()
    # e.g. HealthTech, EdTech
    domain = models.CharField(max_length=100, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ideas_submitted"
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="ideas_team_member",
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    attachment = models.FileField(
        upload_to="ideas/attachments/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class IdeaReview(BaseModelMixin):
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ]
    )

    comments = models.TextField(blank=True)
    recommended = models.BooleanField(default=False)

    class Meta:
        unique_together = ("idea", "reviewer")


class Mentor(BaseModelMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentor_profile"
    )
    # comma-separated or use M2M tag model
    expertise_areas = models.CharField(max_length=255, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    is_external = models.BooleanField(default=False)
    max_mentees = models.PositiveSmallIntegerField(default=5)

    def __str__(self):
        return self.user.get_full_name() or str(self.user)


class MentorAssignment(BaseModelMixin):
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.CASCADE,
        related_name="mentor_assignments"
    )
    mentor = models.ForeignKey(
        'Mentor',
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    assigned_on = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("idea", "mentor")


# ---------------------------------------------------------------------------
# Incubation / Startups
# ---------------------------------------------------------------------------

class Cohort(BaseModelMixin):
    name = models.CharField(max_length=100)  # e.g. "Cohort 2026-A"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Startup(BaseModelMixin):
    class Stage(models.TextChoices):
        IDEATION = "ideation", "Ideation"
        MVP = "mvp", "MVP"
        EARLY_TRACTION = "early_traction", "Early Traction"
        GROWTH = "growth", "Growth"
        GRADUATED = "graduated", "Graduated"
        DISCONTINUED = "discontinued", "Discontinued"

    name = models.CharField(max_length=255)
    idea = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startups"
    )

    cohort = models.ForeignKey(
        'Cohort',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startups"
    )

    founders = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="startups_founded"
    )
    sector = models.CharField(max_length=100, blank=True)
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.IDEATION
    )
    incorporation_date = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to="startups/logos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


class Milestone(BaseModelMixin):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DELAYED = "delayed", "Delayed"

    startup = models.ForeignKey(
        'Startup',
        on_delete=models.CASCADE,
        related_name="milestones"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    class Meta:
        ordering = ["due_date"]


class Resource(BaseModelMixin):
    """Physical resource: lab, co-working desk, meeting room, equipment."""
    class Kind(models.TextChoices):
        LAB = "lab", "Lab"
        WORKSPACE = "workspace", "Workspace/Desk"
        MEETING_ROOM = "meeting_room", "Meeting Room"
        EQUIPMENT = "equipment", "Equipment"

    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


class ResourceBooking(BaseModelMixin):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    resource = models.ForeignKey(
        'Resource',
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bookings"
    )
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_bookings"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )

    class Meta:
        ordering = ["-start_time"]


# ---------------------------------------------------------------------------
# Funding & Grants
# ---------------------------------------------------------------------------

class GrantScheme(BaseModelMixin):
    name = models.CharField(max_length=255)
    # e.g. govt body, internal fund
    funding_agency = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    max_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )
    application_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GrantApplication(BaseModelMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    scheme = models.ForeignKey(
        'GrantScheme',
        on_delete=models.CASCADE,
        related_name="applications"
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grant_applications"
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grant_applications"
    )
    amount_requested = models.DecimalField(max_digits=14, decimal_places=2)
    proposal_document = models.FileField(
        upload_to="grants/proposals/",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    submitted_on = models.DateField(null=True, blank=True)


class SeedFundDisbursement(BaseModelMixin):
    class Tranche(models.TextChoices):
        FIRST = "first", "First Tranche"
        SECOND = "second", "Second Tranche"
        FINAL = "final", "Final Tranche"

    application = models.ForeignKey(
        'GrantApplication',
        on_delete=models.CASCADE,
        related_name="disbursements"
    )
    tranche = models.CharField(max_length=10, choices=Tranche.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    disbursed_on = models.DateField(null=True, blank=True)
    utilization_report = models.FileField(
        upload_to="grants/utilization/",
        blank=True,
        null=True
    )


class Investor(BaseModelMixin):
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True)
    investor_type = models.CharField(
        max_length=100,
        blank=True
    )  # Angel, VC, Corporate
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    focus_sectors = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# IP & Patents
# ---------------------------------------------------------------------------

class InventionDisclosure(BaseModelMixin):
    title = models.CharField(max_length=255)
    disclosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disclosures"
    )
    co_inventors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="co_disclosures",
        blank=True
    )
    startup = models.ForeignKey(
        'Startup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disclosures"
    )

    description = models.TextField()
    disclosure_date = models.DateField(auto_now_add=True)
    document = models.FileField(
        upload_to="ip/disclosures/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class IPRecord(BaseModelMixin):
    class IPType(models.TextChoices):
        PATENT = "patent", "Patent"
        COPYRIGHT = "copyright", "Copyright"
        TRADEMARK = "trademark", "Trademark"
        DESIGN = "design", "Design"

    class Status(models.TextChoices):
        FILED = "filed", "Filed"
        PUBLISHED = "published", "Published"
        GRANTED = "granted", "Granted"
        ABANDONED = "abandoned", "Abandoned"

    disclosure = models.ForeignKey(
        'InventionDisclosure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_records"
    )
    ip_type = models.CharField(max_length=20, choices=IPType.choices)
    application_number = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    filing_date = models.DateField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FILED
    )
    jurisdiction = models.CharField(
        max_length=100,
        blank=True
    )  # e.g. "Kenya", "PCT"

    def __str__(self):
        return f"{self.title} ({self.get_ip_type_display()})"


class LicensingAgreement(BaseModelMixin):
    ip_record = models.ForeignKey(
        'IPRecord',
        on_delete=models.CASCADE,
        related_name="licenses"
    )
    licensee_name = models.CharField(max_length=255)
    agreement_date = models.DateField()
    royalty_terms = models.TextField(blank=True)
    document = models.FileField(
        upload_to="ip/licenses/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)


# ---------------------------------------------------------------------------
# R&D Projects
# ---------------------------------------------------------------------------

class ResearchProject(BaseModelMixin):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DISCONTINUED = "discontinued", "Discontinued"

    title = models.CharField(max_length=255)
    principal_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_projects_led"
    )
    co_investigators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="research_projects_co",
        blank=True
    )
    abstract = models.TextField(blank=True)
    funding_source = models.CharField(max_length=255, blank=True)
    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED
    )

    def __str__(self):
        return self.title


class Publication(BaseModelMixin):
    class PubType(models.TextChoices):
        JOURNAL = "journal", "Journal Article"
        CONFERENCE = "conference", "Conference Paper"
        BOOK_CHAPTER = "book_chapter", "Book Chapter"
        PATENT_PUB = "patent_pub", "Patent Publication"

    project = models.ForeignKey(
        'ResearchProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications"
    )
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="publications"
    )
    pub_type = models.CharField(
        max_length=20,
        choices=PubType.choices
    )
    # journal/conference name
    venue = models.CharField(max_length=255, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    document = models.FileField(
        upload_to="research/publications/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class IndustryCollaboration(BaseModelMixin):
    project = models.ForeignKey(
        'ResearchProject',
        on_delete=models.CASCADE,
        related_name="collaborations"
    )
    partner_organization = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    scope = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)


# ---------------------------------------------------------------------------
# Events & Programs
# ---------------------------------------------------------------------------

class InnovationEvent(BaseModelMixin):
    class EventType(models.TextChoices):
        HACKATHON = "hackathon", "Hackathon"
        BOOTCAMP = "bootcamp", "Bootcamp/Workshop"
        PITCH_DAY = "pitch_day", "Pitch Day"
        COMPETITION = "competition", "Innovation Challenge"

    title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_organized"
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    banner = models.ImageField(
        upload_to="events/banners/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title


class EventRegistration(BaseModelMixin):
    event = models.ForeignKey(
        'InnovationEvent',
        on_delete=models.CASCADE,
        related_name="registrations"
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations"
    )
    team_name = models.CharField(max_length=150, blank=True)
    registered_on = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = ("event", "participant")


# ---------------------------------------------------------------------------
# Partnerships
# ---------------------------------------------------------------------------

class IndustryPartner(BaseModelMixin):
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=150, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name


class MemorandumOfUnderstanding(BaseModelMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    partner = models.ForeignKey(
        'IndustryPartner',
        on_delete=models.CASCADE,
        related_name="mous"
    )
    title = models.CharField(max_length=255)
    signed_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    document = models.FileField(
        upload_to="partnerships/mous/",
        blank=True, null=True
    )


class AlumniEntrepreneur(BaseModelMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alumni_entrepreneur_profile"
    )
    graduation_year = models.PositiveIntegerField()
    startup_name = models.CharField(max_length=255, blank=True)
    willing_to_mentor = models.BooleanField(default=False)
    linkedin_url = models.URLField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or str(self.user)
