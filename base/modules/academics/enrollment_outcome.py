"""
Single source of truth for how an enrollment's result is displayed and
counted — used by ResultsView (the portal) and transcript_pdf (the PDF)
so the two can never disagree. Enrollment's own frozen graded_* fields
ARE the outcome record; this module just reads them consistently
instead of letting each caller recompute independently.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict
from .grading_service import get_enrollment_outcome, EnrollmentOutcome  # noqa: F401


@dataclass
class EnrollmentOutcome:
    status: str  # 'pass' | 'fail' | 'in_progress' | 'ungraded'
    score: Optional[Decimal]
    grade_letter: Optional[str]
    grade_points: Optional[Decimal]
    credits_earned: int


def get_enrollment_outcome(enr, published_bucket: Optional[Dict] = None) -> EnrollmentOutcome:
    """
    published_bucket: {'C': Decimal, 'E': Decimal} of this enrollment's
    published CAT/Exam results — used only for the 'in_progress'
    display when the enrollment hasn't finalized yet. Pass None or {}
    if the caller doesn't have it handy.
    """
    if enr.graded_at is not None:
        passed = (
            enr.pass_mark_applied is not None
            and enr.graded_score >= enr.pass_mark_applied
        )

        grade_letter = (
            enr.graded_scale.letter_for(enr.graded_score)
            if enr.graded_scale_id else None
        )

        return EnrollmentOutcome(
            status='pass' if passed else 'fail',
            score=enr.graded_score,
            grade_letter=grade_letter,
            grade_points=enr.grade_points_earned,
            credits_earned=enr.credits_earned,
        )

    bucket = published_bucket or {}
    if bucket:
        parts = [v for v in bucket.values() if v is not None]
        visible_total = sum(parts).quantize(Decimal('0.01')) if parts else None
        return EnrollmentOutcome(
            status='in_progress',
            score=visible_total,
            grade_letter=None,
            grade_points=None,
            credits_earned=0,
        )

    return EnrollmentOutcome(
        status='ungraded',
        score=None,
        grade_letter=None,
        grade_points=None,
        credits_earned=0,
    )
