# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailGenerationResult:
    """
    Returned by every strategy after attempting to generate an email address.

    success:    False means the strategy failed and the caller should fall back
    email:      the generated email address — None if success=False
    message:    human-readable outcome or error
    fallback:   True if the strategy used a local fallback instead of its primary method
                (e.g. API was unreachable, used default_email_strategy instead)
    """
    success:  bool
    email:    Optional[str] = None
    message:  str = ""
    fallback: bool = False


class AbstractEmailGenerationStrategy(ABC):
    """
    Contract every school email generation strategy must implement.

    A strategy takes a registration number and a domain and returns
    a proposed email address. It does NOT check uniqueness and it does NOT
    write anything to the DB. The SchoolEmailGenerator handles both of those.

    ---

    How to register your strategy in settings.py:

        # built-in key
        SCHOOL_EMAIL_STRATEGY = 'default'

        # dotted import path to your subclass
        SCHOOL_EMAIL_STRATEGY = 'myapp.utils.MyCustomStrategy'

        # API config dict (uses ApiEmailGenerationStrategy under the hood)
        SCHOOL_EMAIL_STRATEGY = {
            "url":    "https://api.university.ac.ke/generate-email/",
            "method": "POST",
            "headers": {"Authorization": "Bearer <token>"},
            "timeout": 5,
        }

    ---

    Implementors must follow these rules:

    1. NEVER write to the DB inside generate()
       Uniqueness checking is done by SchoolEmailGenerator.generate_unique()

    2. ALWAYS return an EmailGenerationResult — never raise
       Catch exceptions internally. Return success=False with a message.
       Set fallback=True if you used a local fallback instead of your primary method.

    3. The returned email must be lowercase
       Email addresses are case-insensitive but the DB treats them as strings.
       Always return .lower() to prevent duplicates like 'CS001@x.com' and 'cs001@x.com'.

    4. The domain is always passed in — never hardcode it
       The institution sets SCHOOL_EMAIL_DOMAIN in settings.py.
       Your strategy receives it and uses it.
    """

    @abstractmethod
    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        """
        Generate an institutional email address from a registration number.

        registration_number:  e.g. 'BSC/001/2024', 'CS/00123/2023'
        domain:               e.g. 'university.ac.ke'

        Must return an EmailGenerationResult.
        Must not raise.
        Must return email in lowercase.
        """
        raise NotImplementedError

    def describe(self) -> str:
        """
        Human-readable description of what this strategy does.
        Shown in the admin and management command output.
        Override in your subclass.
        """
        return self.__class__.__name__
