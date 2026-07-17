from base.modules.regulatory import (
    AbstractAgencyBackend,
    ValidationResult,
    GeneratedReport,
    ReportSection
)

from django.db.models import Count
from django.db import models


class CUEBackend(AbstractAgencyBackend):
    agency_code = "cue"
    agency_name = "Commission for University Education"

    def report_types(self):
        return {
            "annual_return": "CUE Annual Statistical Return",
            "capacity_compliance": "CUE Capacity Compliance Check",
        }

    def generate_report(self, report) -> GeneratedReport | None:
        generators = {
            "annual_return": self._annual_return,
            "capacity_compliance": self._capacity_compliance,
        }
        fn = generators.get(report.report_type)
        return fn(report) if fn else None

    # --- individual section builders, kept small and testable ---
    def _enrollment_section(self, session) -> ReportSection:
        from base.models import Enrollment

        rows = (
            Enrollment.objects
            .filter(session=session)
            .values('programme__code', 'programme__programme_name', 'programme__level')
            .annotate(total=Count('id'), disabled=Count('id', filter=models.Q(is_disabled=True)))
            .order_by('programme__code')
        )
        return ReportSection(
            title="Enrollment by programme",
            headers=["Programme code", "Programme name", "Level",
                     "Total enrolled", "Students with disabilities"],
            rows=[[r['programme__code'], r['programme__programme_name'],
                   r['programme__level'], r['total'], r['disabled']] for r in rows],
        )

    def _staff_section(self, session) -> ReportSection:
        from base.models import LecturerAssignment

        rows = (
            LecturerAssignment.objects
            .filter(session=session)
            .values('staff__name', 'staff__qualification', 'staff__department__department_name')
            .annotate(courses_taught=Count('course', distinct=True))
            .order_by('staff__department__department_name', 'staff__name')
        )
        return ReportSection(
            title="Staffing and qualifications",
            headers=["Name", "Qualification", "Department", "Courses taught"],
            rows=[
                [
                    r['staff__name'],
                    r['staff__qualification'],
                    r['staff__department__department_name'],
                    r['courses_taught']
                ] for r in rows
            ],
        )

    def _deferment_section(self, session) -> ReportSection:
        from base.models import Deferment

        rows = (
            Deferment.objects
            .filter(session=session)
            .values('student__programme__code')
            .annotate(total=Count('id'))
            .order_by('student__programme__code')
        )
        return ReportSection(
            title="Deferments this session",
            headers=["Programme code", "Deferments"],
            rows=[
                [
                    r['student__programme__code'],
                    r['total']
                ] for r in rows
            ],
        )

    def _annual_return(self, report) -> GeneratedReport:
        session = report.session
        return GeneratedReport(
            sections=[
                self._enrollment_section(session),
                self._staff_section(session),
                self._deferment_section(session),
            ],
            filename=f"CUE-annual-return-{session.academic_year.replace('/', '-')}-S{session.semester}.xlsx",
        )

    def _capacity_compliance(self, report) -> GeneratedReport:
        from base.models import Programme, Enrollment

        rows = []
        for p in Programme.objects.filter(status="Active"):
            enrolled = Enrollment.objects.filter(
                programme=p,
                session=report.session
            ).count()

            rows.append(
                [
                    p.code,
                    p.programme_name,
                    p.capacity,
                    enrolled,
                    "Over" if enrolled > p.capacity else "OK"
                ]
            )

        return GeneratedReport(
            sections=[
                ReportSection(
                    title="Programme capacity vs CUE-approved cap",
                    headers=[
                        "Code",
                        "Programme",
                        "Approved capacity",
                        "Enrolled",
                        "Status"
                    ],
                    rows=rows,
                )],
            filename=f"CUE-capacity-check-{report.session.academic_year.replace('/', '-')}.xlsx",
        )

    def validate_submission(self, report) -> ValidationResult:
        if not report.documents.exists():
            return ValidationResult(False, ["CUE requires a signed transmittal or data sheet."])
        return ValidationResult(True)

    def validate_accreditation(self, accreditation) -> ValidationResult:
        errors = []
        if accreditation.accreditation_type == "Programme" and not accreditation.programme:
            errors.append(
                "Programme accreditation must reference a specific programme."
            )
        if self.enforces_capacity_cap() and accreditation.programme:
            if accreditation.programme.capacity <= 0:
                errors.append(
                    "CUE-approved capacity must be set before accreditation is Active."
                )
        return ValidationResult(not errors, errors)

    def enforces_capacity_cap(self) -> bool:
        return True   # CUE caps intake per approved capacity

    def renewal_lead_time_days(self) -> int:
        return 180
