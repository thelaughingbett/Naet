import requests
from typing import Optional, Callable
from base.modules.email_generation.base import (
    AbstractEmailGenerationStrategy,
    EmailGenerationResult,
)
from base.modules.email_generation.strategies.builtin import DefaultEmailStrategy


class ApiEmailGenerationStrategy(AbstractEmailGenerationStrategy):
    """
    Calls an external API to generate the email address.
    Falls back to DefaultEmailStrategy if the API is unreachable.

    The API must accept:
        POST {"registration_number": "BSC/001/2024", "domain": "university.ac.ke"}

    And respond with:
        {"email": "bsc001@university.ac.ke"}

    Both the payload shape and response shape are customisable via
    payload_builder and response_parser.

    Usage — direct:
        strategy = ApiEmailGenerationStrategy(
            url="https://api.university.ac.ke/generate-email/",
            headers={"Authorization": "Bearer <token>"},
        )

    Usage — from settings dict (handled by SchoolEmailGenerator._resolve_strategy):
        SCHOOL_EMAIL_STRATEGY = {
            "url":    "https://api.university.ac.ke/generate-email/",
            "method": "POST",
            "headers": {"Authorization": "Bearer <token>"},
            "timeout": 5,
        }
    """

    def __init__(
        self,
        url:              str,
        method:           str = "POST",
        headers:          Optional[dict] = None,
        payload_builder:  Optional[Callable] = None,
        response_parser:  Optional[Callable] = None,
        timeout:          int = 5,
    ):
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.payload_builder = payload_builder or self._default_payload
        self.response_parser = response_parser or self._default_parser
        self.timeout = timeout
        self._fallback = DefaultEmailStrategy()

    @staticmethod
    def _default_payload(registration_number: str, domain: str) -> dict:
        return {"registration_number": registration_number, "domain": domain}

    @staticmethod
    def _default_parser(data: dict) -> str:
        return data["email"]

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        payload = self.payload_builder(registration_number, domain)

        try:
            if self.method == "GET":
                response = requests.get(
                    self.url, params=payload, headers=self.headers, timeout=self.timeout
                )
            else:
                response = requests.post(
                    self.url, json=payload, headers=self.headers, timeout=self.timeout
                )

            response.raise_for_status()
            email = self.response_parser(response.json()).lower()

            return EmailGenerationResult(
                success=True,
                email=email,
                message=f"Generated via API: {self.url}",
            )

        except (requests.RequestException, KeyError, ValueError) as e:
            # API failed — fall back to local default
            fallback_result = self._fallback.generate(
                registration_number, domain)
            return EmailGenerationResult(
                success=True,
                email=fallback_result.email,
                message=f"API unavailable ({e}) — used local fallback",
                fallback=True,
            )

    def describe(self):
        return f"API strategy — {self.method} {self.url}"
