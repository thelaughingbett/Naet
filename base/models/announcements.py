from base.models import BaseModelMixin, ValidatedFileMixin
from django.db import models


class AnnouncementDocument(ValidatedFileMixin, BaseModelMixin):
    """
    Slides, briefs, or other files a lecturer attaches to an announcement.
    Portal-delivered only — SMS notifications carry a link, not the file.
    """

    announcement = models.ForeignKey(
        'Announcement',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='lecturer_announcements/%Y/%m/')
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. Lecture slides, assignment brief"
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in the portal attachment list"
    )

    allowed_mime_types = {
        '.pdf':  ['application/pdf'],
        '.doc':  ['application/msword'],
        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        '.ppt':  ['application/vnd.ms-powerpoint'],
        '.pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        '.png':  ['image/png'],
        '.jpg':  ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.zip':  ['application/zip'],
    }
    # slides can be large, but keep it below report doc's cap
    max_size_bytes = 15 * 1024 * 1024

    class Meta:
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Doc for {self.announcement.title}: {self.original_name}"


class Announcement(BaseModelMixin):
    """
    Lecturer posts to a class or the whole department.
    Delivered via notification engine — SMS for urgent, portal for normal.
    """

    SCOPE_CHOICES = [
        ('class',      'Specific class'),
        ('curriculum', 'Specific unit'),
        ('dept',       'Whole department'),
    ]

    author = models.ForeignKey('User', on_delete=models.PROTECT)
    title = models.CharField(max_length=255)
    body = models.TextField()
    scope = models.CharField(max_length=15, choices=SCOPE_CHOICES)

    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # TODO : scope to assigned courses i.e change to lecturer assignment
    )

    is_urgent = models.BooleanField(default=False)
    # urgent=True → fire SMS via notification engine
    published_at = models.DateTimeField(null=True, blank=True)
