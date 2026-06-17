"""
School Email Generation Module

This module provides a pluggable architecture for generating institutional
email addresses from student registration numbers. A strategy takes a
registration number and a domain and proposes an email address.
Uniqueness checking and database writes are handled exclusively by
SchoolEmailGenerator in generator.py — never inside a strategy.


Folder Structure Reference:
    base/modules/email_generation/
    ├── __init__.py          # This file
    ├── base.py              # AbstractEmailGenerationStrategy + EmailGenerationResult
    ├── generator.py         # SchoolEmailGenerator — uniqueness, conflict resolution,
    │                        # strategy resolution, and the global email_generator instance
    └── strategies/
        ├── __init__.py
        ├── builtin.py       # DefaultEmailStrategy, InitialsYearStrategy, NumericOnlyStrategy
        ├── api_strategy.py  # ApiEmailGenerationStrategy — delegates to an external API
        │                    # with automatic fallback to DefaultEmailStrategy
        ├── examples/
        │   └── custom.py    # UOELDStrategy — institution-specific reference implementation
        └── contrib/
            └── __init__.py  # Community-contributed strategies


Built-in Strategies:

    default  →  strategies/builtin.py :: DefaultEmailStrategy
        The simplest format — programme prefix + serial number.
        Used as the system fallback when no strategy is configured.
        BSC/001/2024 → bsc001@domain

    initials_year  →  strategies/builtin.py :: InitialsYearStrategy
        Includes the intake year — avoids collisions when serial
        numbers reset each academic year.
        BSC/001/2024 → bsc001.2024@domain

    numeric_only  →  strategies/builtin.py :: NumericOnlyStrategy
        Strips all non-digit characters. For institutions that require
        purely numeric email local parts.
        BSC/001/2024 → 0012024@domain

    api  →  strategies/api_strategy.py :: ApiEmailGenerationStrategy
        Delegates generation to an external HTTP API. Falls back to
        DefaultEmailStrategy automatically if the API is unreachable.
        Payload and response shapes are customisable via callables.


Configuration (settings.py):

    The SchoolEmailGenerator reads two settings:

        SCHOOL_EMAIL_DOMAIN   = 'university.ac.ke'    # required

        SCHOOL_EMAIL_STRATEGY = ...                   # optional, defaults to 'default'

    SCHOOL_EMAIL_STRATEGY accepts three forms:

    1. Built-in strategy key (string):

        SCHOOL_EMAIL_STRATEGY = 'default'
        SCHOOL_EMAIL_STRATEGY = 'initials_year'
        SCHOOL_EMAIL_STRATEGY = 'numeric_only'

    2. Dotted import path to a subclass of AbstractEmailGenerationStrategy:

        SCHOOL_EMAIL_STRATEGY = 'myapp.utils.MyCustomStrategy'

    3. API config dict (uses ApiEmailGenerationStrategy under the hood):

        SCHOOL_EMAIL_STRATEGY = {
            "url":     "https://api.university.ac.ke/generate-email/",
            "method":  "POST",
            "headers": {"Authorization": "Bearer <token>"},
            "timeout": 5,
        }


Usage:

    The module exposes a pre-configured global instance — import and call it directly:

        from base.modules.email_generation import email_generator

        # generate (raises ValueError on failure)
        email = email_generator.generate('BSC/001/2024')

        # generate with uniqueness guarantee
        email = email_generator.generate_unique('BSC/001/2024')

    For one-off overrides (e.g. in tests or management commands):

        from base.modules.email_generation.generator import SchoolEmailGenerator
        from base.modules.email_generation.strategies.builtin import InitialsYearStrategy

        generator = SchoolEmailGenerator(
            domain='override.ac.ke',
            strategy=InitialsYearStrategy(),
        )
        email = generator.generate_unique('BSC/001/2024')


Writing a Custom Strategy:

    Subclass AbstractEmailGenerationStrategy and implement generate():

        from base.modules.email_generation.base import (
            AbstractEmailGenerationStrategy,
            EmailGenerationResult,
        )

        class MyCustomStrategy(AbstractEmailGenerationStrategy):
            def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
                try:
                    # build your email address here
                    email = f"...@{domain}".lower()
                    return EmailGenerationResult(success=True, email=email)
                except Exception as e:
                    return EmailGenerationResult(success=False, message=str(e))

            def describe(self) -> str:
                return "My format — REG/NUM/YEAR → ... @domain"

    See strategies/examples/custom.py (UOELDStrategy) for a full reference.
    Place local strategies in  strategies/
    Place contributed strategies in  strategies/contrib/


Execution Contract:
    - generate() must never raise — catch all exceptions internally.
    - generate() must never write to the database — SchoolEmailGenerator owns that.
    - generate() must never check uniqueness — SchoolEmailGenerator.generate_unique() owns that.
    - Always return email in lowercase — the DB treats email addresses as plain strings.
    - Always use the domain parameter — never hardcode a domain inside a strategy.
    - Return EmailGenerationResult(success=False, message=str(e)) on any failure.
    - Set fallback=True on the result if a local fallback was used instead of
      the primary method (e.g. API was unreachable).
"""

from base.modules.email_generation.base import (
    AbstractEmailGenerationStrategy,
    EmailGenerationResult,
)
from base.modules.email_generation.generator import email_generator

__all__ = [
    'AbstractEmailGenerationStrategy',
    'EmailGenerationResult',
    'email_generator',
]
