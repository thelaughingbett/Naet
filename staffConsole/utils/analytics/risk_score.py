"""
At-risk student risk scoring.

Two layers, deliberately kept separate:
  - gather_risk_inputs(student, term)   -> hits the DB, returns raw numbers
  - score_from_inputs(inputs)           -> pure function, no DB, easy to unit test

compute_student_risk_score() glues them together for normal use.

Run this file directly (`python risk_score.py`) to see score_from_inputs()
work standalone with sample data — no Django project required for that part.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RiskScoreResult:
    score: Decimal
    tier: str  # "green" | "amber" | "red"
    contributing_factors: dict = field(default_factory=dict)
    hard_triggers: list = field(default_factory=list)
    notes: list = field(default_factory=list)  # informational, non-scored (e.g. medical context)


# ---------------------------------------------------------------------------
# Weights — must sum to 1.0
# ---------------------------------------------------------------------------

WEIGHTS = {
    "gpa": Decimal("0.25"),
    "academic_standing": Decimal("0.20"),
    "backlog": Decimal("0.15"),
    "enrollment_churn": Decimal("0.10"),
    "financial_hold": Decimal("0.10"),
    "deferment_history": Decimal("0.08"),
    "grievance": Decimal("0.07"),
    "housing_instability": Decimal("0.05"),
}
assert sum(WEIGHTS.values()) == Decimal("1.00"), "Risk weights must sum to 1.00"

TIER_THRESHOLDS = (
    (Decimal("65"), "red"),
    (Decimal("35"), "amber"),
    (Decimal("0"), "green"),
)


# ---------------------------------------------------------------------------
# Layer 1 — gather raw inputs from the database (Django-dependent)
# ---------------------------------------------------------------------------

def gather_risk_inputs(student, term, pass_threshold: Decimal = Decimal("40.00")) -> dict:
    """
    Pull every raw signal needed for scoring, for one student in one term.
    Returns plain Python values only (no querysets, no model instances) so
    the result can be cached, logged, or fed straight into score_from_inputs().
    """
    from django.db.models import Q

    inputs = {}

    # --- GPA ---------------------------------------------------------------
    degree_audit = getattr(student, "degree_audit", None)
    inputs["gpa"] = float(degree_audit.gpa) if degree_audit and degree_audit.gpa is not None else None
    inputs["academic_standing_deficient"] = bool(
        degree_audit and degree_audit.result == "deficient"
    )

    # --- Backlogs ------------------------------------------------------------
    backlogs = student.backlog_registrations.all()
    inputs["backlog_count"] = backlogs.count()
    inputs["max_backlog_attempt"] = max(
        (b.attempt_number for b in backlogs), default=1
    )

    # --- Failed graded components this term ---------------------------------
    failed_results = 0
    total_results = 0
    for enrollment in student.enrollment_records.filter(curriculum__session=term):
        for result in enrollment.results.all():
            total_results += 1
            if result.score is not None and result.score < pass_threshold:
                failed_results += 1
    inputs["failed_component_ratio"] = (
        failed_results / total_results if total_results else 0.0
    )

    # --- Revaluation frequency this term -------------------------------------
    inputs["revaluation_count"] = student.revaluation_requests.filter(
        result__enrollment__curriculum__session=term
    ).count()

    # --- Enrollment churn (dropped courses this term) ------------------------
    term_enrollments = student.enrollment_records.filter(curriculum__session=term)
    total_enrollments = term_enrollments.count()
    dropped = term_enrollments.filter(status="dropped").count()
    inputs["enrollment_churn_ratio"] = dropped / total_enrollments if total_enrollments else 0.0

    # --- Deferment history -----------------------------------------------------
    all_deferments = student.deferments.all()
    inputs["deferment_count"] = all_deferments.count()
    inputs["has_active_deferment"] = all_deferments.filter(status="active").exists()

    # --- Financial hold (boolean only — never expose the balance itself) --------
    fee_account = student.fee_accounts.filter(fee_structure__session=term).first()
    inputs["financial_hold"] = bool(fee_account and not fee_account.is_cleared)

    # --- Active/critical grievances --------------------------------------------
    open_complaints = student.complaints.filter(
        Q(status="Open") | Q(status="Escalated") | Q(status="In_Progress")
    )
    inputs["has_critical_complaint"] = open_complaints.filter(priority="Critical").exists()
    inputs["open_complaint_count"] = open_complaints.count()

    # --- Housing instability -----------------------------------------------------
    vacated_this_term = student.hostel_allocations.filter(
        session=term, status="VACATED"
    ).exists()
    low_hostel_rating = False
    allocation = student.hostel_allocations.filter(session=term).first()
    if allocation is not None and hasattr(allocation, "evaluation"):
        low_hostel_rating = allocation.evaluation.rating <= 2
    inputs["housing_instability"] = vacated_this_term or low_hostel_rating

    # --- Health context (annotation only, never scored as risk) -----------------
    sick_days = sum(
        e.recommended_sick_leave_days
        for e in student.clinic_visits.filter(date_of_visit__year=getattr(term, "start_date", None) and term.start_date.year)
    )
    inputs["documented_sick_leave_days"] = sick_days

    return inputs


# ---------------------------------------------------------------------------
# Layer 2 — pure scoring function (no DB access — unit-testable in isolation)
# ---------------------------------------------------------------------------

def score_from_inputs(inputs: dict) -> RiskScoreResult:
    """
    Turn the raw signal dict from gather_risk_inputs() into a risk score.
    Pure function: same input always produces the same output, no side effects.
    """
    factors = {}
    hard_triggers = []
    notes = []

    # --- GPA component: 2.5 GPA -> 0 risk, 0.0 GPA -> full risk -------------
    gpa = inputs.get("gpa")
    if gpa is None:
        factors["gpa"] = 0.0
        notes.append("No DegreeAudit on file — GPA component skipped, not penalized.")
    else:
        factors["gpa"] = max(0.0, min(1.0, (2.5 - gpa) / 2.5))

    # --- Academic standing ----------------------------------------------------
    factors["academic_standing"] = 1.0 if inputs.get("academic_standing_deficient") else 0.0
    if inputs.get("academic_standing_deficient"):
        hard_triggers.append("deficient_academic_standing")

    # --- Backlog component -----------------------------------------------------
    backlog_count = inputs.get("backlog_count", 0)
    max_attempt = inputs.get("max_backlog_attempt", 1)
    factors["backlog"] = min(1.0, (backlog_count * 0.25) + ((max_attempt - 1) * 0.15))

    # Failed components feed into the backlog signal too (early warning
    # before a failed component officially becomes a backlog registration)
    failed_ratio = inputs.get("failed_component_ratio", 0.0)
    factors["backlog"] = min(1.0, factors["backlog"] + failed_ratio * 0.3)

    # --- Enrollment churn --------------------------------------------------------
    factors["enrollment_churn"] = min(1.0, inputs.get("enrollment_churn_ratio", 0.0) * 2)

    # --- Financial hold (binary) ---------------------------------------------------
    factors["financial_hold"] = 1.0 if inputs.get("financial_hold") else 0.0

    # --- Deferment history -----------------------------------------------------------
    deferment_count = inputs.get("deferment_count", 0)
    factors["deferment_history"] = min(1.0, deferment_count * 0.4)
    if inputs.get("has_active_deferment"):
        hard_triggers.append("active_deferment")
        factors["deferment_history"] = 1.0

    # --- Grievance flag ------------------------------------------------------------------
    if inputs.get("has_critical_complaint"):
        factors["grievance"] = 1.0
        hard_triggers.append("critical_complaint")
    elif inputs.get("open_complaint_count", 0) > 0:
        factors["grievance"] = 0.5
    else:
        factors["grievance"] = 0.0

    # --- Housing instability ---------------------------------------------------------------
    factors["housing_instability"] = 1.0 if inputs.get("housing_instability") else 0.0

    # --- Composite score -----------------------------------------------------------------------
    raw_score = sum(
        Decimal(str(factors[key])) * weight for key, weight in WEIGHTS.items()
    ) * 100
    score = raw_score.quantize(Decimal("0.01"))

    # --- Tier, with hard-trigger override ----------------------------------------------------------
    tier = _tier_for_score(score)
    if hard_triggers and tier == "green":
        tier = "amber"  # a single severe flag can't be averaged away

    # --- Health context note (informational only, doesn't affect score) -------------------------------
    sick_days = inputs.get("documented_sick_leave_days", 0)
    if sick_days > 0:
        notes.append(f"{sick_days} documented sick-leave day(s) this term — consider before escalating.")

    return RiskScoreResult(
        score=score,
        tier=tier,
        contributing_factors={k: round(v, 3) for k, v in factors.items()},
        hard_triggers=hard_triggers,
        notes=notes,
    )


def _tier_for_score(score: Decimal) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "green"


# ---------------------------------------------------------------------------
# Combined entry point for normal (Django) use
# ---------------------------------------------------------------------------

def compute_student_risk_score(student, term) -> RiskScoreResult:
    """
    Convenience wrapper: gather_risk_inputs() + score_from_inputs() in one call.
    Use this from a management command / Celery task iterating over a cohort.

    Example:
        for student in Student.objects.filter(class_entered__programme=programme):
            result = compute_student_risk_score(student, current_session)
            StudentRiskScore.objects.update_or_create(
                student=student, term=current_session,
                defaults=dict(
                    score=result.score, tier=result.tier,
                    contributing_factors=result.contributing_factors,
                    hard_triggers=result.hard_triggers,
                ),
            )
    """
    inputs = gather_risk_inputs(student, term)
    return score_from_inputs(inputs)


# ---------------------------------------------------------------------------
# Standalone demo — run `python risk_score.py` to see score_from_inputs() work
# with no database at all.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_students = {
        "Healthy student": {
            "gpa": 3.4, "academic_standing_deficient": False,
            "backlog_count": 0, "max_backlog_attempt": 1,
            "failed_component_ratio": 0.0, "revaluation_count": 0,
            "enrollment_churn_ratio": 0.0, "deferment_count": 0,
            "has_active_deferment": False, "financial_hold": False,
            "has_critical_complaint": False, "open_complaint_count": 0,
            "housing_instability": False, "documented_sick_leave_days": 0,
        },
        "Quietly slipping": {
            "gpa": 2.1, "academic_standing_deficient": False,
            "backlog_count": 1, "max_backlog_attempt": 1,
            "failed_component_ratio": 0.2, "revaluation_count": 1,
            "enrollment_churn_ratio": 0.15, "deferment_count": 0,
            "has_active_deferment": False, "financial_hold": True,
            "has_critical_complaint": False, "open_complaint_count": 0,
            "housing_instability": False, "documented_sick_leave_days": 0,
        },
        "Hard-trigger case": {
            "gpa": 2.9, "academic_standing_deficient": False,
            "backlog_count": 0, "max_backlog_attempt": 1,
            "failed_component_ratio": 0.0, "revaluation_count": 0,
            "enrollment_churn_ratio": 0.0, "deferment_count": 1,
            "has_active_deferment": True, "financial_hold": False,
            "has_critical_complaint": False, "open_complaint_count": 0,
            "housing_instability": False, "documented_sick_leave_days": 0,
        },
        "Full crisis": {
            "gpa": 1.4, "academic_standing_deficient": True,
            "backlog_count": 3, "max_backlog_attempt": 2,
            "failed_component_ratio": 0.4, "revaluation_count": 2,
            "enrollment_churn_ratio": 0.3, "deferment_count": 1,
            "has_active_deferment": False, "financial_hold": True,
            "has_critical_complaint": True, "open_complaint_count": 1,
            "housing_instability": True, "documented_sick_leave_days": 12,
        },
    }

    for name, inputs in sample_students.items():
        result = score_from_inputs(inputs)
        print(f"\n{name}")
        print(f"  score={result.score}  tier={result.tier}")
        print(f"  hard_triggers={result.hard_triggers}")
        print(f"  factors={result.contributing_factors}")
        if result.notes:
            print(f"  notes={result.notes}")
