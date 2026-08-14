# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.conf import settings
from django.utils import timezone
from base.managers import CommonUnitCurriculumManager
from .base import BaseModelMixin
from simple_history.models import HistoricalRecords
from django.db import models
from django.core.exceptions import ValidationError

ASSIGNMENT_STATUS_CHOICES = [
    ('Draft', 'Draft Assignment'),
    ('Assigned', 'Assigned / Pending Review'),
    ('Confirmed', 'Confirmed by Head of Department'),
    ('Substituted', 'Substituted / Relieved'),
]


class Syllabus(BaseModelMixin):
    """
    The catalog-level link between a Programme and a Course. Declares that
    this course is (or is proposed to be, or was) part of this programme's
    curriculum

    `Curriculum` points here instead of directly at `Course`, so scheduling
    can only draw from courses actually approved for that programme.
    """

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"    # core/required, active
        # elective/supplementary, active but optional
        ADJUNCT = "adjunct", "Adjunct"
        RETIRED = "retired", "Retired"        # no longer offered under this programme

    # States a Curriculum entry is actually allowed to schedule against.
    SCHEDULABLE_STATES = (State.APPROVED, State.ADJUNCT)

    programme = models.ForeignKey(
        "Programme",
        on_delete=models.PROTECT,
        related_name="syllabus_entries"
    )
    course = models.ForeignKey(
        "Course",
        on_delete=models.PROTECT,
        related_name="syllabus_entries"
    )

    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PROPOSED
    )

    year_introduced = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Academic year this entry was approved/introduced into the programme",
    )

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="syllabus_proposals",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="syllabus_approvals",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("programme", "course")
        verbose_name_plural = "Syllabus entries"

    def clean(self):
        super().clean()
        if self.state == self.State.APPROVED and not self.approved_by:
            raise ValidationError({
                "approved_by": "An approving user is required before a syllabus "
                "entry can move to Approved."
            })

    def __str__(self):
        return f"{self.programme} — {self.course} [{self.get_state_display()}]"


class Curriculum(BaseModelMixin):
    """
    Represents an active teaching slot pairing a course unit with a specific
    class/cohort during an academic session.
    """

    Tclass = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT
    )

    syllabus = models.ForeignKey(
        'Syllabus',
        on_delete=models.PROTECT,
        related_name='curriculum_entries',
    )

    professor = models.ManyToManyField(
        'Lecturer',
        through='LecturerAssignment',
        related_name='assigned_curricula',
        blank=True
    )  # TODO : change name to lecturer not professor

    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name="curricula"
    )

    weekly_allocated_slots = models.PositiveIntegerField(
        default=3,
        help_text="Weekly instructional contact hours allocated to this curriculum for this unit."
    )  # for timetabling and other purposes

    history = HistoricalRecords()

    capacity = models.PositiveIntegerField(default=60)

    class Meta:
        unique_together = ('syllabus', 'Tclass', 'session')
        verbose_name = "Curriculum Slot"
        verbose_name_plural = "Curriculum Slots"

    @property
    def results(self):
        """All Result rows for students enrolled in this curriculum slot."""
        from base.models import Result
        return Result.objects.filter(
            enrollment__curriculum=self
        ).select_related('enrollment__student')

    def __str__(self):
        return f"{self.course} - {self.Tclass} - {self.session}"

    @property
    def course(self):
        return self.syllabus.course

    def clean(self):
        super().clean()
        if self.syllabus.state not in Syllabus.SCHEDULABLE_STATES:
            raise ValidationError({
                'syllabus': f"Cannot schedule a class into a course that is "
                f"'{self.syllabus.get_state_display()}' — only "
                f"Approved or Adjunct syllabus entries can be taught."
            })
        if self.syllabus.programme_id != self.Tclass.programme_id:
            raise ValidationError({
                'syllabus': f"This syllabus entry belongs to "
                f"{self.syllabus.programme}, not {self.Tclass.programme}."
            })

    @classmethod
    def clone_curriculum(cls, from_session_id, to_session_id):
        """
        Clones all curriculum allocations from one session to another,
        maintaining the respective lecturer assignments under a 'Draft' state.

        FIXED: previously referenced `course`/`course_id`, which no longer
        exist as real fields on Curriculum (course is now a @property
        proxying `syllabus.course`) — this raised TypeError/AttributeError
        on every call since the Syllabus refactor. Now uses `syllabus`/
        `syllabus_id` throughout.

        ALSO FIXED: the source queryset now excludes any Curriculum whose
        syllabus entry is no longer in a SCHEDULABLE_STATE. bulk_create()
        never calls clean(), so without this filter a Retired or
        still-Proposed syllabus entry could get silently cloned into the
        next session's timetable — exactly what Curriculum.clean() exists
        to prevent for normal creates.
        """
        source = cls.objects.filter(
            session_id=from_session_id,
            syllabus__state__in=Syllabus.SCHEDULABLE_STATES,
        ).select_related('syllabus').prefetch_related('professor')

        professor_map = {}
        new_records = []
        for req in source:
            obj = cls(
                syllabus=req.syllabus,
                Tclass=req.Tclass,
                session_id=to_session_id,
            )
            new_records.append(obj)
            professor_map[(req.syllabus_id, req.Tclass_id)
                          ] = list(req.professor.all())

        cls.objects.bulk_create(new_records, ignore_conflicts=True)

        created = cls.objects.filter(
            session_id=to_session_id,
            syllabus_id__in=[r.syllabus_id for r in new_records],
            Tclass_id__in=[r.Tclass_id for r in new_records],
        )
        for obj in created:
            professors = professor_map.get(
                (obj.syllabus_id, obj.Tclass_id), [])
            if professors:
                obj.professor.set(professors)

        return created.count()


class LecturerAssignment(BaseModelMixin):
    """
    Through-table tracking the allocation of lecturers to specific course slots.
    Captures operational metrics required for CUE workload compliance reporting.
    """
    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.CASCADE,
        related_name='lecturer_assignments'
    )

    lecturer = models.ForeignKey(
        'Lecturer',
        on_delete=models.PROTECT,
        related_name='curriculum_assignments'
    )

    is_primary = models.BooleanField(
        default=True,
        verbose_name="Primary Instructor",
        help_text="True if this lecturer is the main resource lead grading exams."
    )

    allocated_workload_hours = models.PositiveIntegerField(
        default=3,
        help_text="Weekly instructional contact hours allocated to this lecturer for this unit."
    )

    status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default='Assigned'
    )

    date_assigned = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('curriculum', 'lecturer')
        verbose_name = "Lecturer Assignment"
        verbose_name_plural = "Lecturer Assignments"

    def clean(self):
        """
        CUE Safety Rules: Enforces structural workload constraints across tables.
        """
        super().clean()

        if self.curriculum and self.lecturer:
            # 1. Enforce Primary Instructor Constraints
            # A course slot can only have exactly ONE primary lecturer at a time
            if self.is_primary:
                clashing_primaries = LecturerAssignment.objects.filter(
                    curriculum=self.curriculum,
                    is_primary=True
                ).exclude(pk=self.pk)

                if clashing_primaries.exists():
                    raise ValidationError({
                        'is_primary': "A curriculum class slot can only have one primary instructor assigned. "
                                      "Please set subsequent resources as assistants/co-lecturers."
                    })

            # 2. Maximum Workload Multi-Table Aggregation Safeguard
            # Pull total hours assigned to this teacher during the active session cycle
            current_total_workload = LecturerAssignment.objects.filter(
                lecturer=self.lecturer,
                curriculum__session=self.curriculum.session
            ).exclude(pk=self.pk).aggregate(total=models.Sum('allocated_workload_hours'))['total'] or 0

            # CUE Quality Rule: Hard ceiling on active part-time/full-time weekly contact hours (e.g., max 40 hours)
            if (current_total_workload + self.allocated_workload_hours) > 40:
                raise ValidationError({
                    'allocated_workload_hours': f"CUE Compliance Alert: This assignment pushes the lecturer's total weekly "
                    f"workload to {current_total_workload + self.allocated_workload_hours} hours, "
                    f"violating institutional capacity guidelines (Max: 40 hours)."
                })

    def __str__(self):
        role = "Primary" if self.is_primary else "Assistant"
        return f"{self.lecturer} - {self.curriculum.course.course_code} ({role})"


class CommonUnitCurriculum(Curriculum):
    objects = CommonUnitCurriculumManager()

    class Meta:
        proxy = True
        verbose_name = 'Common Unit'
        verbose_name_plural = 'Common Units'

    @property
    def classes(self):
        """
        FIXED: previously filtered only on `session=self.session` +
        `syllabus__course__course_type='CC'`, which returns every class
        taking ANY common-unit course this session, not classes sharing
        THIS specific common unit. Scoping to `syllabus=self.syllabus`
        restores "all classes sharing this course + session".
        """
        return Curriculum.objects.filter(
            session=self.session,
            syllabus=self.syllabus,
        ).values_list('Tclass__class_name', flat=True)


class Enrollment(BaseModelMixin):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ("dropped", "Dropped"),
        # write a signal or method to update this once moved to next academic year [most likely a celery job should suffice here else heavy workload] 👇🏿
        ("completed", "Completed")
    ]

    APPROVAL_METHOD_CHOICES = [
        ('system', 'System auto-approved'),
        ('manual', 'Manually approved'),
    ]

    # Core, Common Unit — default behavior only now
    AUTO_APPROVE_COURSE_TYPES = ('C', 'CC')

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )
    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending'
    )

    approval_method = models.CharField(
        max_length=10,
        choices=APPROVAL_METHOD_CHOICES,
        null=True,
        blank=True,
        default='system',
        help_text="Set only when status='approved'. Distinguishes a system "
        "auto-approval from a human overriding/confirming it — "
        "core units can go either way, so this can't be inferred "
        "from approved_by alone."
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_enrollments',
        help_text="Null when approval_method='system'. Set to the reviewer "
        "when approval_method='manual'."
    )

    # TODO : make sure save updates this
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'curriculum')

    def __str__(self):
        return f"{self.student} → {self.curriculum} [{self.status}]"

    @property
    def requires_manual_approval(self) -> bool:
        """
        Default behavior for new enrollments — not a hard restriction.
        A core/common unit can still be manually approved via approve().

        NOTE — not changed here, flagging only: this still reads
        `self.curriculum.course.course_type`, i.e. Course's single GLOBAL
        Core/Elective/Common flag. Now that Syllabus exists specifically to
        let a course be Core for one programme and Adjunct/elective for
        another, this is the natural place to actually use that —
        e.g. `self.curriculum.syllabus.state == Syllabus.State.ADJUNCT`
        instead of (or alongside) `course_type`. Left as-is since switching
        this changes which enrollments auto-approve — worth doing
        deliberately rather than as a drive-by fix.
        """
        return self.curriculum.course.course_type not in self.AUTO_APPROVE_COURSE_TYPES

    def clean(self):
        super().clean()

        from base.models import RegistrationWindow
        from django.core.exceptions import ValidationError
        window = (
            RegistrationWindow.objects.filter(
                term=self.curriculum.session,
                window_type=RegistrationWindow.WindowType.COURSE_REGISTRATION,  # check for errors here
            )
            # possible BUG
            .filter(models.Q(programme=self.student.class_entered.programme) | models.Q(programme__isnull=True))
            # prefer a program-specific window over an institution-wide one
            .order_by("programme")
            .first()
        )

        if window is None:
            raise ValidationError(
                "No course registration window has been configured for this term.")
        if not window.is_open:
            raise ValidationError(
                "Course registration is closed for this term.")

        if self.status == 'approved':
            if not self.approved_at:
                raise ValidationError({
                    'approved_at': "approved_at is required when status is 'approved'."
                })
            if not self.approval_method:
                raise ValidationError({
                    'approval_method': "approval_method is required when status is 'approved'."
                })
            if self.approval_method == 'system' and self.approved_by_id:
                raise ValidationError({
                    'approved_by': "A system-approved enrollment shouldn't carry a human approver. "
                    "Use approval_method='manual' if a reviewer signed off."
                })
            if self.approval_method == 'manual' and not self.approved_by_id:
                raise ValidationError({
                    'approved_by': "Manual approval requires the reviewing user."
                })
        else:
            if self.approved_by_id or self.approved_at or self.approval_method:
                raise ValidationError({
                    'status': "approval_method/approved_by/approved_at should only be set "
                              "when status is 'approved'."
                })

    def save(self, *args, **kwargs):
        # default auto-approval on first save — only kicks in if nothing
        # has already set status/approval_method (i.e. approve() wasn't
        # called explicitly first)
        if self._state.adding and self.status == 'pending' and not self.requires_manual_approval:
            self.status = 'approved'
            self.approval_method = 'system'
            self.approved_by = None
            self.approved_at = timezone.now()

        self.full_clean()
        super().save(*args, **kwargs)

    def approve(self, by_user):
        """Manual approval — for electives by default, but also usable to
        have a human confirm/override a core or common unit enrollment."""
        self.status = 'approved'
        self.approval_method = 'manual'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, by_user, reason=""):
        self.status = 'rejected'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.approval_method = None
        self.save()


class Result(BaseModelMixin):
    type_result = [
        ('C', 'Cat'),
        ('E', 'Exams'),
        ('P', 'Practicals'),
        ('A', 'Assignments'),
        ('Q', 'Quizzes'),
        ('PR', 'Projects'),
    ]

    RESULT_STATE_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for approval'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('disputed', 'Disputed'),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name='results'
    )

    entered_by = models.ForeignKey(
        'User',
        on_delete=models.DO_NOTHING
    )  # non-repudiation field to track who touched record tracked by historical records

    type = models.CharField(
        choices=type_result,
        default='C',
        max_length=45
    )

    state = models.CharField(
        choices=RESULT_STATE_CHOICES,
        default='draft',
        max_length=20,
    )

    score = models.DecimalField(
        decimal_places=2,
        max_digits=5
    )

    title = models.CharField(
        max_length=124
    )

    history = HistoricalRecords()

    def clean(self):

        if self.type != 'E' and self.type != 'PR':
            self.state = 'published'

        return super().clean()

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enrollment.student} - {self.title}"
