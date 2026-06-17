import datetime

from base.models.base import BaseModelMixin

from django.db import models


class EventItem(BaseModelMixin):
    external_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    # "Academic", "Sports", "Social"
    category = models.CharField(max_length=50)

    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    location = models.CharField(max_length=255, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    meeting_url = models.URLField(null=True, blank=True)  # Zoom/Teams link

    badge = models.CharField(max_length=50, null=True, blank=True)
    thumbnail = models.URLField(null=True, blank=True)

    # full details / registration
    source_url = models.URLField(null=True, blank=True)
    source_name = models.CharField(max_length=100)

    # external registration form
    rsvp_url = models.URLField(null=True, blank=True)
    rsvp_deadline = models.DateField(null=True, blank=True)

    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'start_time']

    @property
    def status(self):
        today = datetime.date.today()
        if self.date > today:
            return 'upcoming'
        if self.date == today:
            return 'ongoing'
        return 'past'

    @property
    def is_rsvp_open(self):
        if not self.rsvp_url:
            return False
        if self.rsvp_deadline:
            return datetime.date.today() <= self.rsvp_deadline
        return self.status == 'upcoming'


class NewsItem(BaseModelMixin):
    """
    Lightweight card-data store for news from external CMS.
    Never stores full article content — just enough to render a card.
    source_url is the redirect to the full article.
    """
    external_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    category = models.CharField(max_length=50)
    date = models.DateField()
    source_url = models.URLField()
    source_name = models.CharField(max_length=100)
    badge = models.CharField(max_length=50, null=True, blank=True)
    thumbnail = models.URLField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.title
