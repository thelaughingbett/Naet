from base.modules.email_generation.base import (
    AbstractEmailGenerationStrategy,
    EmailGenerationResult,
)


class UOELDStrategy(AbstractEmailGenerationStrategy):
    """
    Institution-specific format.
    BSC/001/2024 → student.001.2024@uoeld.ac.ke
    """

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        try:
            parts = registration_number.split('/')
            if len(parts) < 3:
                return EmailGenerationResult(
                    success=False,
                    message=f"Expected format PROG/NUM/YEAR, got '{registration_number}'"
                )
            email = f"student.{parts[1]}.{parts[2]}@{domain}".lower()
            return EmailGenerationResult(success=True, email=email)
        except Exception as e:
            return EmailGenerationResult(success=False, message=str(e))

    def describe(self):
        return "UOELD format — BSC/001/2024 → student.001.2024@domain"
