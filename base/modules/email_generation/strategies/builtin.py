import re
from base.modules.email_generation.base import (
    AbstractEmailGenerationStrategy,
    EmailGenerationResult,
)


class DefaultEmailStrategy(AbstractEmailGenerationStrategy):
    """
    BSC/001/2024 → BSC001@domain
    The simplest possible strategy — prefix + serial number.
    Used as the fallback when nothing else is configured.
    """

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        try:
            parts = registration_number.split('/')
            if len(parts) >= 2:
                email = f"{parts[0]}{parts[1]}@{domain}".lower()
            else:
                email = f"{registration_number.replace('/', '')}@{domain}".lower()

            return EmailGenerationResult(success=True, email=email)
        except Exception as e:
            return EmailGenerationResult(success=False, message=str(e))

    def describe(self):
        return "Default — programme prefix + serial number (BSC/001/2024 → bsc001@domain)"


class InitialsYearStrategy(AbstractEmailGenerationStrategy):
    """
    BSC/001/2024 → bsc001.2024@domain
    Includes the year — useful when serial numbers reset per year.
    """

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        try:
            parts = registration_number.split('/')
            if len(parts) >= 3:
                email = f"{parts[0].lower()}{parts[1]}.{parts[2]}@{domain}"
            else:
                # fall through to default
                email = f"{registration_number.replace('/', '').lower()}@{domain}"

            return EmailGenerationResult(success=True, email=email)
        except Exception as e:
            return EmailGenerationResult(success=False, message=str(e))

    def describe(self):
        return "Initials + year — BSC/001/2024 → bsc001.2024@domain"


class NumericOnlyStrategy(AbstractEmailGenerationStrategy):
    """
    BSC/001/2024 → 0012024@domain
    Strips everything except digits. Good for numeric-only email systems.
    """

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        try:
            numeric = re.sub(r'\D', '', registration_number)
            if not numeric:
                return EmailGenerationResult(
                    success=False,
                    message=f"No digits found in registration number '{registration_number}'"
                )
            email = f"{numeric}@{domain}".lower()
            return EmailGenerationResult(success=True, email=email)
        except Exception as e:
            return EmailGenerationResult(success=False, message=str(e))

    def describe(self):
        return "Numeric only — BSC/001/2024 → 0012024@domain"
