from abc import ABC
from dataclasses import dataclass, field


@dataclass
class ReportSection:
    title:   str
    headers: list[str]
    rows:    list[list]


@dataclass
class GeneratedReport:
    sections: list[ReportSection]
    filename: str
    format:   str = "xlsx"   # 'xlsx' | 'csv' | 'pdf'


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


class AbstractAgencyBackend(ABC):
    """
    One backend per real-world body (CUE, Engineers Board of Kenya,
    Nursing Council, KASNEB...). A body may support reporting,
    accrediting, both, or neither yet — capabilities are optional
    overrides, not required abstract methods, so a minimal backend
    with just agency_code/agency_name is still valid and registrable.
    """

    agency_code: str = ""
    agency_name: str = ""

    # ---- reporting capability (RegulatoryReport) ----
    def validate_submission(self, report) -> ValidationResult:
        return ValidationResult(valid=True)   # no special rules by default

    def submission_document_types(self) -> list[str]:
        return ['.pdf', '.csv', '.xlsx']

    # ---- accrediting capability (Accreditation) ----
    def validate_accreditation(self, accreditation) -> ValidationResult:
        return ValidationResult(valid=True)

    def renewal_lead_time_days(self) -> int:
        """How far ahead of expiry a renewal must be initiated."""
        return 180

    def enforces_capacity_cap(self) -> bool:
        """Does this body cap intake numbers per programme (like CUE's approved capacity)?"""
        return False

    def accreditation_evidence_types(self, accreditation_type: str) -> list[str]:
        return ['.pdf']

    def generate_report(self, report) -> GeneratedReport | None:
        """
        Build the data payload for this report from live DB state.
        Return None if this agency/report type has no auto-generation
        (some CUE submissions are still hand-compiled narrative docs).
        """
        return None

    def report_types(self) -> dict[str, str]:
        """{code: display_name} of report kinds this agency supports generating."""
        return {}
