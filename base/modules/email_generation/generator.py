from typing import Optional, Callable
from django.conf import settings

from base.modules.email_generation.base import AbstractEmailGenerationStrategy
from base.modules.email_generation.strategies.builtin import (
    DefaultEmailStrategy,
    InitialsYearStrategy,
    NumericOnlyStrategy,
)


BUILT_IN_STRATEGIES = {
    'default':       DefaultEmailStrategy,
    'initials_year': InitialsYearStrategy,
    'numeric_only':  NumericOnlyStrategy,
}


class SchoolEmailGenerator:
    """
    Generates institutional email addresses from registration numbers.

    Reads SCHOOL_EMAIL_DOMAIN and SCHOOL_EMAIL_STRATEGY from settings.py.
    Handles uniqueness checking and conflict resolution.

    settings.py options:

        SCHOOL_EMAIL_DOMAIN   = 'university.ac.ke'

        # built-in strategy key
        SCHOOL_EMAIL_STRATEGY = 'default'

        # dotted import path to a subclass of AbstractEmailGenerationStrategy
        SCHOOL_EMAIL_STRATEGY = 'myapp.utils.MyCustomStrategy'

        # API config dict
        SCHOOL_EMAIL_STRATEGY = {
            "url":    "https://api.university.ac.ke/generate-email/",
            "method": "POST",
            "headers": {"Authorization": "Bearer <token>"},
            "timeout": 5,
        }
    """

    def __init__(
        self,
        domain:   Optional[str] = None,
        strategy: Optional[AbstractEmailGenerationStrategy] = None,
    ):
        self.domain = domain or getattr(
            settings, 'SCHOOL_EMAIL_DOMAIN', 'institution.ac.ke')
        self.strategy = strategy or self._resolve_strategy()

    def _resolve_strategy(self) -> AbstractEmailGenerationStrategy:
        setting = getattr(settings, 'SCHOOL_EMAIL_STRATEGY', 'default')

        # dict → API strategy
        if isinstance(setting, dict):
            from base.modules.email_generation.strategies.apistrategy import ApiEmailGenerationStrategy
            return ApiEmailGenerationStrategy(
                url=setting['url'],
                method=setting.get('method', 'POST'),
                headers=setting.get('headers'),
                payload_builder=setting.get('payload_builder'),
                response_parser=setting.get('response_parser'),
                timeout=setting.get('timeout', 5),
            )

        # built-in string key
        if isinstance(setting, str):
            if setting in BUILT_IN_STRATEGIES:
                return BUILT_IN_STRATEGIES[setting]()

            # dotted import path to a subclass
            try:
                from django.utils.module_loading import import_string
                cls = import_string(setting)
                if not issubclass(cls, AbstractEmailGenerationStrategy):
                    raise TypeError(
                        f"'{setting}' must be a subclass of AbstractEmailGenerationStrategy"
                    )
                return cls()
            except (ImportError, TypeError):
                return DefaultEmailStrategy()

        # already an instance
        if isinstance(setting, AbstractEmailGenerationStrategy):
            return setting

        return DefaultEmailStrategy()

    def generate(self, registration_number: str) -> str:
        """Generate an email address. Returns the email string or raises ValueError."""
        result = self.strategy.generate(registration_number, self.domain)
        if not result.success:
            raise ValueError(
                f"Email generation failed for '{registration_number}': {result.message}"
            )
        return result.email

    def is_unique(self, email: str) -> bool:
        from base.models import Student
        return not Student.objects.filter(school_email=email).exists()

    def generate_unique(self, registration_number: str) -> str:
        """
        Generate an email address guaranteed to be unique in the DB.
        Appends a counter suffix if the base address is taken.

        BSC001@domain → BSC001.2@domain → BSC001.3@domain → ...
        """
        base_email = self.generate(registration_number)

        if self.is_unique(base_email):
            return base_email

        local, domain = base_email.split('@')
        counter = 2
        while True:
            candidate = f"{local}.{counter}@{domain}"
            if self.is_unique(candidate):
                return candidate
            counter += 1


email_generator = SchoolEmailGenerator()
