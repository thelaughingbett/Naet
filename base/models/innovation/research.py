# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.conf import settings
from django.db import models

from ..base import BaseModelMixin


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
