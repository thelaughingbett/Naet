# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
base/modules/academics/grading_service.py

THE ONE PLACE a score becomes a grade.

Every view/model that shows or stores a final score, letter, grade points,
pass/fail, GPA, classification or "can progress" goes through here. Nothing
else may carry its own cut-offs, its own weighting loop, or its own idea of
which Result rows count. That is what keeps the lecturer's Enter-Results page,
the class list, the student's results page, the transcript and
Enrollment.finalize_grade() from disagreeing.

THE RULES (each one was a source of drift before):

 1. FROZEN WINS. Once Enrollment.graded_at is set, the stored graded_score /
    grade_points_earned / credits_earned are the truth, and the letter is read
    from the scale that was applied then (graded_scale), not today's.

 2. FROZEN IS NOT AUTOMATICALLY VISIBLE. Lock & Transmit freezes a grade while
    Exam/Project results are still 'submitted' (awaiting HOD approval). A
    viewer whose `states` exclude any result that fed the frozen grade must
    NOT see the frozen number yet - they get "in progress" until those
    results are released. (Lecturers use PREVIEW and see everything.)

 3. ONE FORMULA when not frozen: WeightingComponent.compute() per component
    (best-N, latest-N, effective_score caps...) -> weighted sum -> band lookup.
    An incomplete component makes the whole score None: "in progress", never
    a partial number.

 4. WHICH RESULTS COUNT is an explicit, named choice (`states`):
        PREVIEW   every state            (lecturer, pre-lock)
        FINALIZE  published + submitted  (what Lock & Transmit freezes)
        PUBLISHED published only         (what a student may see)

 5. READS NEVER WRITE. Only finalize() freezes a grade.

 6. GPA / CGPA / classification / progression are computed HERE from outcomes,
    never re-derived in JavaScript or in a second view.

Callers create one GradingService() per request: it caches resolved policies
for that request only (never module-global, so a policy edit is never stale).

No model imports at import time (Result is imported lazily) -> no import cycle.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone

TWO_PLACES = Decimal('0.01')

# ── which Result states count ────────────────────────────────────────────────
PREVIEW = None                         # every state, drafts included
FINALIZE = ('published', 'submitted')  # what Lock & Transmit freezes
PUBLISHED = ('published',)             # what a student may see

# ── outcome status strings ───────────────────────────────────────────────────
PASS = 'pass'
FAIL = 'fail'
UNGRADED = 'in_progress'               # not enough results yet / not released

# ── institution rules (one place) ────────────────────────────────────────────
PROGRESSION_MIN_GPA = Decimal('2.00')
CLASSIFICATION = (                     # (min cgpa, label), best first
    (Decimal('3.6'), 'First Class Honours'),
    (Decimal('3.0'), 'Second Class Honours (Upper)'),
    (Decimal('2.5'), 'Second Class Honours (Lower)'),
    (Decimal('2.0'), 'Pass'),
)
CLASSIFICATION_FLOOR = 'Probation'


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────
class _ListQS:
    """
    Lets WeightingComponent.compute() run on an in-memory list (it only calls
    .order_by()), so the real aggregation logic is reused untouched.
    """

    def __init__(self, items):
        self._items = items

    def order_by(self, *args, **kwargs):
        return self._items


def _safe(fn):
    try:
        return fn()
    except (ValidationError, AttributeError, ObjectDoesNotExist):
        return None


def _in_states(result, states):
    return states is None or result.state in states


# ─────────────────────────────────────────────────────────────────────────────
# Value objects
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class GradingPolicy:
    """The rules a score is judged by: weighting scheme, scale, pass mark."""
    scheme: object
    scale: object
    components: tuple
    bands: tuple                      # sorted highest min_score first
    pass_mark: Optional[int]

    def band_for(self, score):
        """Highest band whose min_score <= score, or None."""
        return next((b for b in self.bands if b.min_score <= score), None)

    @property
    def grade_labels(self):
        """Letters in display order (best first) - for filter dropdowns."""
        seen, out = set(), []
        for b in self.bands:
            label = b.label or str(b.grade_points)
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out


@dataclass(frozen=True)
class EnrollmentOutcome:
    """What the UI needs about one enrollment."""
    status: str                       # pass | fail | in_progress
    score: Optional[Decimal]          # weighted final, None until complete
    grade_letter: str                 # '' until complete
    grade_points: Optional[Decimal]
    passed: Optional[bool]
    credits_earned: int
    complete: bool
    frozen: bool                      # True = read from the stored, frozen grade
    # result_type -> Decimal|None
    components: dict = field(default_factory=dict)
    pass_mark: Optional[int] = None

    @property
    def final(self):
        return self.score


# ─────────────────────────────────────────────────────────────────────────────
# Pure functions (no DB) - the formula itself
# ─────────────────────────────────────────────────────────────────────────────
def build_policy(scheme, scale, pass_mark):
    components = tuple(scheme.components.all()) if scheme else ()
    bands = (
        tuple(sorted(scale.bands.all(), key=lambda b: -b.min_score))
        if scale else ()
    )
    return GradingPolicy(scheme, scale, components, bands, pass_mark)


def component_scores(policy, results):
    """{result_type: aggregated score | None} using each component's own rule."""
    out = {}
    for comp in policy.components:
        items = sorted(
            (r for r in results if r.type == comp.result_type),
            key=lambda r: r.record_id,
        )
        out[comp.result_type] = comp.compute(_ListQS(items))
    return out


def weighted_score(policy, comp_scores):
    """Weighted final to 2dp, or None if any component is not yet complete."""
    if not policy.components:
        return None
    total = Decimal('0')
    for comp in policy.components:
        s = comp_scores.get(comp.result_type)
        if s is None:
            return None
        total += Decimal(str(s)) * (comp.weight_percent / Decimal('100'))
    return total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _label(band):
    return (band.label or str(band.grade_points)) if band else ''


def _status(passed):
    if passed is None:
        return UNGRADED
    return PASS if passed else FAIL


def evaluate(policy, results, credits=0):
    """results -> EnrollmentOutcome, purely from the policy (never frozen)."""
    comps = component_scores(policy, results)
    score = weighted_score(policy, comps)

    if score is None:
        return EnrollmentOutcome(
            status=UNGRADED, score=None, grade_letter='', grade_points=None,
            passed=None, credits_earned=0, complete=False, frozen=False,
            components=comps, pass_mark=policy.pass_mark,
        )

    band = policy.band_for(score)
    passed = None if policy.pass_mark is None else score >= policy.pass_mark
    return EnrollmentOutcome(
        status=_status(passed), score=score,
        grade_letter=_label(band),
        grade_points=band.grade_points if band else None,
        passed=passed,
        credits_earned=credits if passed else 0,
        complete=True, frozen=False,
        components=comps, pass_mark=policy.pass_mark,
    )


# ── GPA / classification / progression (rule 6) ──────────────────────────────
def gpa_summary(entries, dedupe=False):
    """
    entries: iterable of (course_code, EnrollmentOutcome, credits).
    Only graded outcomes (pass/fail) count; in-progress units are ignored.

    dedupe=True keeps the FIRST entry per course_code - callers pass newest
    first so a retake replaces the earlier attempt (used for CGPA). Per-session
    and per-year summaries leave it False.
    """
    seen = set()
    gpa_credits = credits_earned = units_failed = 0
    points = Decimal('0')

    for code, o, credits in entries:
        if o.status not in (PASS, FAIL):
            continue
        if dedupe:
            if code in seen:
                continue
            seen.add(code)
        gpa_credits += credits
        points += (o.grade_points or Decimal('0')) * credits
        credits_earned += o.credits_earned or 0
        if o.status == FAIL:
            units_failed += 1

    gpa = ((points / gpa_credits).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
           if gpa_credits else Decimal('0.00'))
    return {
        'credits':        gpa_credits,        # credits that count towards GPA
        'credits_earned': credits_earned,
        'points':         points,
        'gpa':            gpa,
        'units_failed':   units_failed,
    }


def classify(cgpa):
    cgpa = Decimal(str(cgpa))
    for floor, label in CLASSIFICATION:
        if cgpa >= floor:
            return label
    return CLASSIFICATION_FLOOR


def can_progress(summary):
    return (summary['gpa'] >= PROGRESSION_MIN_GPA
            and summary['units_failed'] == 0)


def summary_json(summary):
    """JSON-safe copy of a gpa_summary dict."""
    return {k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in summary.items()}


# ─────────────────────────────────────────────────────────────────────────────
# The service (DB-aware)
# ─────────────────────────────────────────────────────────────────────────────
class GradingService:
    """Create one per request. See module docstring for the rules."""

    def __init__(self):
        self._policies = {}

    # ── policy resolution ────────────────────────────────────────────────────
    def policy_for(self, curriculum, scheme=None):
        """
        The LIVE policy for a curriculum. `scheme` asks "what if it used THAT
        scheme?" (the Change-weighting impact preview) without touching the DB.
        """
        key = ('live', curriculum.record_id,
               getattr(scheme, 'record_id', None))
        if key not in self._policies:
            course = curriculum.course
            self._policies[key] = build_policy(
                scheme or _safe(curriculum.get_weighting_scheme),
                _safe(course.get_grading_scale),
                course.pass_mark,
            )
        return self._policies[key]

    def _frozen_policy(self, enrollment):
        """The policy that produced an already-frozen grade (rule 1)."""
        course = enrollment.curriculum.course
        key = ('frozen', enrollment.weighting_scheme_used_id,
               enrollment.graded_scale_id, enrollment.pass_mark_applied)
        if key not in self._policies:
            live = self.policy_for(enrollment.curriculum)
            scheme = (enrollment.weighting_scheme_used
                      if enrollment.weighting_scheme_used_id else live.scheme)
            scale = (enrollment.graded_scale
                     if enrollment.graded_scale_id else live.scale)
            pass_mark = (enrollment.pass_mark_applied
                         if enrollment.pass_mark_applied is not None
                         else course.pass_mark)
            self._policies[key] = build_policy(scheme, scale, pass_mark)
        return self._policies[key]

    def policy_of(self, enrollment):
        """The policy actually in force for THIS enrollment (frozen or live)."""
        if enrollment.graded_at is not None and enrollment.graded_score is not None:
            return self._frozen_policy(enrollment)
        return self.policy_for(enrollment.curriculum)

    # ── fetching results ─────────────────────────────────────────────────────
    def fetch_results(self, enrollment_ids, states=PREVIEW):
        """{str(enrollment_id): [Result, ...]} in ONE query."""
        from base.models import Result      # lazy: no import cycle
        qs = (Result.objects
              .filter(enrollment_id__in=list(enrollment_ids))
              .select_related('enrollment__curriculum__course'))
        if states is not None:
            qs = qs.filter(state__in=states)
        by_enr = {}
        for r in qs:
            by_enr.setdefault(str(r.enrollment_id), []).append(r)
        return by_enr

    # ── outcomes ─────────────────────────────────────────────────────────────
    def evaluate(self, policy, results, credits=0):
        """Pure evaluation against an explicit policy (used for what-ifs)."""
        return evaluate(policy, results, credits)

    def outcome(self, enrollment, results=None, states=PUBLISHED):
        """
        The single answer to "how is this enrollment doing?".

        `results` must be the enrollment's results in ALL states (pass the
        list you already loaded to avoid a query). They are filtered by
        `states` here, so a caller can never accidentally widen the view.
        """
        if results is None:
            results = self.fetch_results(
                [enrollment.record_id], PREVIEW
            ).get(str(enrollment.record_id), [])

        visible = [r for r in results if _in_states(r, states)]
        credits = enrollment.curriculum.course.credits

        if enrollment.graded_at is not None and enrollment.graded_score is not None:
            # Rule 2: a frozen grade is only shown once every result that fed
            # it is visible to this viewer.
            unreleased = [r for r in results
                          if _in_states(r, FINALIZE) and not _in_states(r, states)]
            if not unreleased:
                return self._frozen_outcome(enrollment, results)
            return evaluate(self._frozen_policy(enrollment), visible, credits)

        return evaluate(self.policy_for(enrollment.curriculum), visible, credits)

    def outcomes(self, enrollments, states=PUBLISHED):
        """{str(enrollment_id): EnrollmentOutcome} - one results query total."""
        enrollments = list(enrollments)
        by_enr = self.fetch_results(
            [e.record_id for e in enrollments], PREVIEW)
        return {
            str(e.record_id): self.outcome(
                e, results=by_enr.get(str(e.record_id), []), states=states)
            for e in enrollments
        }

    def _frozen_outcome(self, enrollment, results):
        policy = self._frozen_policy(enrollment)
        score = enrollment.graded_score
        band = policy.band_for(score)
        pm = enrollment.pass_mark_applied
        passed = None if pm is None else score >= pm
        points = (enrollment.grade_points_earned
                  if enrollment.grade_points_earned is not None
                  else (band.grade_points if band else None))
        # Component scores are display-only here (the final is NOT recomputed).
        comps = component_scores(
            policy, [r for r in results if _in_states(r, FINALIZE)])
        return EnrollmentOutcome(
            status=_status(passed), score=score, grade_letter=_label(band),
            grade_points=points, passed=passed,
            credits_earned=enrollment.credits_earned or 0,
            complete=True, frozen=True, components=comps, pass_mark=pm,
        )

    def score_for(self, enrollment, states=FINALIZE):
        """Weighted final from live results, ignoring any frozen value."""
        results = self.fetch_results(
            [enrollment.record_id], states).get(str(enrollment.record_id), [])
        policy = self.policy_for(enrollment.curriculum)
        if not policy.components:
            raise ValidationError(
                "No weighting scheme is configured for this course."
                if not policy.scheme else
                f"Weighting scheme '{policy.scheme.name}' has no components configured.")
        return weighted_score(policy, component_scores(policy, results))

    # ── the only write ───────────────────────────────────────────────────────
    def finalize(self, enrollment, *, force=False, states=FINALIZE):
        """
        Freeze an enrollment's grade. Returns False if already graded (no
        force) or not enough results yet; raises ValidationError for broken
        configuration (no scheme / scale / pass mark / covering band).
        """
        if enrollment.graded_at is not None and not force:
            return False

        curriculum = enrollment.curriculum
        course = curriculum.course
        policy = self.policy_for(curriculum)

        score = self.score_for(enrollment, states)
        if score is None:
            return False

        if policy.scale is None:
            raise ValidationError(
                "No grading scale is configured for this course.")
        if policy.pass_mark is None:
            raise ValidationError("This course has no pass mark configured.")
        band = policy.band_for(score)
        if band is None:
            raise ValidationError(
                f"Grading scale '{policy.scale.name}' has no band covering a score "
                f"of {score} - it needs a band with min_score=0 as a floor.")

        passed = score >= policy.pass_mark
        enrollment.graded_score = score
        enrollment.grade_points_earned = band.grade_points
        enrollment.credits_earned = course.credits if passed else 0
        enrollment.graded_scale = policy.scale
        enrollment.weighting_scheme_used = policy.scheme
        enrollment.pass_mark_applied = policy.pass_mark
        enrollment.graded_at = timezone.now()
        enrollment.save(update_fields=[
            'graded_score', 'grade_points_earned', 'credits_earned',
            'graded_scale', 'weighting_scheme_used', 'pass_mark_applied',
            'graded_at',
        ])
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Back-compat for the old base.modules.academics.enrollment_outcome module.
# `bucket` (a hand-built {type: score} dict) is ignored on purpose.
# ─────────────────────────────────────────────────────────────────────────────
def get_enrollment_outcome(enrollment, bucket=None, *, service=None):
    return (service or GradingService()).outcome(enrollment, states=PUBLISHED)
