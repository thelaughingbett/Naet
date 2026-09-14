# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Curriculum / scheduling domain.

Owns the question "what is being taught, by whom, to which class, in
which session" — from catalog-level approval (Syllabus) down to the
actual teaching slot (Curriculum) and its staffing (LecturerAssignment).

Grading policy (WeightingScheme) and student outcomes (Enrollment,
Result) live in sibling modules; this module only exposes
`get_weighting_scheme()` as a resolution helper for those modules to
call into.
"""

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


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

    offered = models.IntegerField(
        default=1,
        help_text="Year of study this unit is typically scheduled."
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
    Now represents a shared teaching slot for one Course in one Session —
    potentially serving several classes across different programmes at
    once (e.g. an Informatics section and a CS section attending the
    same lecture). Which classes attend, and under what syllabus
    approval, is tracked via CurriculumClass below — not a direct FK.
    """

    course = models.ForeignKey(
        'Course',
        on_delete=models.PROTECT,
        related_name='curriculum_entries',
    )

    classes = models.ManyToManyField(
        'Tclass',
        through='CurriculumClass',
        related_name='curricula',
    )

    professor = models.ManyToManyField(
        'Lecturer',
        through='LecturerAssignment',
        related_name='assigned_curricula',
        blank=True
    )

    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name="curricula"
    )

    weekly_allocated_slots = models.PositiveIntegerField(default=3)
    history = HistoricalRecords()
    capacity = models.PositiveIntegerField(
        default=60,
        help_text="Total seats across ALL classes attending this slot, "
        "not per-class. Enrollment capacity checks must sum across "
        "every class now, not assume one Tclass per Curriculum."
    )

    weighting_scheme_override = models.ForeignKey(
        'WeightingScheme', on_delete=models.PROTECT, null=True, blank=True,
        related_name='curricula_overriding',
    )

    class Meta:
        unique_together = ('course', 'session')
        verbose_name = "Curriculum Slot"
        verbose_name_plural = "Curriculum Slots"

    def __str__(self):
        class_names = ", ".join(
            self.classes.values_list('class_name', flat=True))
        return f"{self.course} - [{class_names}] - {self.session}"

    def get_weighting_scheme(self):
        if self.weighting_scheme_override_id:
            return self.weighting_scheme_override
        return self.course.get_weighting_scheme()

    @classmethod
    def clone_curriculum(cls, from_session_id, to_session_id, keep_professor=True):
        """
        Clones curriculum slots from one session to another.

        Curriculum has no direct `syllabus`/`Tclass` fields — those live on
        CurriculumClass, one row per (curriculum, Tclass), each carrying its
        own `syllabus`. So schedulability has to be checked per class-link,
        not per Curriculum: a shared slot might have one class whose
        Syllabus entry is still Approved and another that's since been
        Retired, and only the former should be carried into the new session.
        A Curriculum whose class-links are all unschedulable is skipped
        entirely rather than cloned with zero classes attached.

        Lecturer assignments are carried over reset to 'Draft', matching the
        original intent of re-confirming staffing each session rather than
        silently inheriting Confirmed status.

        get_or_create is used throughout instead of bulk_create so reruns
        (e.g. after a partial failure) don't violate the unique_together
        constraints on Curriculum/CurriculumClass/LecturerAssignment.
        Note this bypasses clean() (as bulk_create did before it) — none of
        the model-level ValidationError checks run here, only the
        SCHEDULABLE_STATES filter below.
        """
        source_curricula = cls.objects.filter(
            session_id=from_session_id
        ).prefetch_related(
            'class_links__syllabus',
            'lecturer_assignments',
        )

        slots_created = 0
        links_created = 0

        for old_curriculum in source_curricula:
            schedulable_links = [
                link for link in old_curriculum.class_links.all()
                if link.syllabus.state in Syllabus.SCHEDULABLE_STATES
            ]
            if not schedulable_links:
                continue  # nothing left worth scheduling for this slot

            new_curriculum, created = cls.objects.get_or_create(
                course_id=old_curriculum.course_id,
                session_id=to_session_id,
                defaults={
                    'weekly_allocated_slots': old_curriculum.weekly_allocated_slots,
                    'capacity': old_curriculum.capacity,
                    'weighting_scheme_override_id': old_curriculum.weighting_scheme_override_id,
                },
            )
            if created:
                slots_created += 1

            for link in schedulable_links:
                _, link_created = CurriculumClass.objects.get_or_create(
                    curriculum=new_curriculum,
                    Tclass_id=link.Tclass_id,
                    defaults={'syllabus_id': link.syllabus_id},
                )
                if link_created:
                    links_created += 1

            if keep_professor:
                for assignment in old_curriculum.lecturer_assignments.all():
                    LecturerAssignment.objects.get_or_create(
                        curriculum=new_curriculum,
                        lecturer_id=assignment.lecturer_id,
                        defaults={
                            'is_primary': assignment.is_primary,
                            'allocated_workload_hours': assignment.allocated_workload_hours,
                            'status': 'Draft',
                        },
                    )

        return {'slots_created': slots_created, 'links_created': links_created}


class CurriculumClass(BaseModelMixin):
    """
    Links one Tclass to a shared Curriculum slot, recording the specific
    Syllabus entry that authorizes THAT class's programme to take this
    course — preserving per-programme approval even when the teaching
    slot itself is shared across programmes.
    """

    curriculum = models.ForeignKey(
        'Curriculum', on_delete=models.CASCADE, related_name='class_links'
    )
    Tclass = models.ForeignKey(
        'Tclass', on_delete=models.PROTECT, related_name='curriculum_links'
    )
    syllabus = models.ForeignKey(
        'Syllabus', on_delete=models.PROTECT, related_name='curriculum_links'
    )

    class Meta:
        unique_together = ('curriculum', 'Tclass')
        verbose_name = "Curriculum Class Link"

    def clean(self):
        super().clean()
        if self.syllabus.course_id != self.curriculum.course_id:
            raise ValidationError({
                'syllabus': "This syllabus entry is for a different course "
                f"than {self.curriculum.course}."
            })
        if self.syllabus.programme_id != self.Tclass.programme_id:
            raise ValidationError({
                'syllabus': f"This syllabus entry belongs to "
                f"{self.syllabus.programme}, not {self.Tclass.programme}."
            })


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
