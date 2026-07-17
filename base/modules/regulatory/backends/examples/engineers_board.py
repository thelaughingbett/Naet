from base.modules.regulatory import (AbstractAgencyBackend, ValidationResult)


class EngineersBoardBackend(AbstractAgencyBackend):
    agency_code = "ebk"
    agency_name = "Engineers Board of Kenya"

    # no validate_submission override → this body isn't a reporting target,
    # it only accredits, so the base "always valid" default is correct here

    def validate_accreditation(self, accreditation) -> ValidationResult:
        if accreditation.accreditation_type != "Specialized":
            return ValidationResult(False, ["EBK accreditation must be type 'Specialized'."])
        return ValidationResult(True)

    def renewal_lead_time_days(self) -> int:
        return 365   # EBK wants renewal applications a full year out

    def accreditation_evidence_types(self, accreditation_type):
        return ['.pdf', '.zip']   # site-visit report bundles
