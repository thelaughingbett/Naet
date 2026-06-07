# utils/email_generator.py

import re
import requests
from django.conf import settings
from typing import Callable, Optional


# ── Built-in local strategies (fallback / no-API) ────────────────────────────

def default_email_strategy(registration_number: str, domain: str) -> str:
    parts = registration_number.split('/')
    if len(parts) >= 2:
        return f"{parts[0].upper()}{parts[1]}@{domain}"
    return f"{registration_number.replace('/', '').upper()}@{domain}"


def initials_year_strategy(registration_number: str, domain: str) -> str:
    parts = registration_number.split('/')
    if len(parts) >= 3:
        return f"{parts[0].lower()}{parts[1]}.{parts[2]}@{domain}"
    return default_email_strategy(registration_number, domain)


def numeric_only_strategy(registration_number: str, domain: str) -> str:
    numeric = re.sub(r'\D', '', registration_number)
    return f"{numeric}@{domain}"


# ── API strategy factory ──────────────────────────────────────────────────────

def make_api_strategy(
    url: str,
    method: str = "POST",
    payload_builder: Optional[Callable] = None,
    response_parser: Optional[Callable] = None,
    headers: Optional[dict] = None,
    timeout: int = 5,
) -> Callable:
    """
    Factory that returns an API-backed strategy function.

    Args:
        url:              The API endpoint.
        method:           HTTP method ('GET' or 'POST').
        payload_builder:  fn(reg_num, domain) → dict sent as JSON body / params.
                          Defaults to {"registration_number": reg_num, "domain": domain}
        response_parser:  fn(response_json) → email string.
                          Defaults to response_json["email"]
        headers:          Extra request headers (e.g. Authorization).
        timeout:          Seconds before the request times out.

    Usage:
        my_strategy = make_api_strategy(
            url="https://api.myschool.ac.ke/generate-email/",
            headers={"Authorization": "Bearer <token>"},
            payload_builder=lambda reg, domain: {"reg": reg, "domain": domain},
            response_parser=lambda data: data["generated_email"],
        )
    """
    def _default_payload(reg_num: str, domain: str) -> dict:
        return {"registration_number": reg_num, "domain": domain}

    def _default_parser(data: dict) -> str:
        return data["email"]

    builder = payload_builder or _default_payload
    parser = response_parser or _default_parser

    def api_strategy(registration_number: str, domain: str) -> str:
        payload = builder(registration_number, domain)
        try:
            if method.upper() == "GET":
                resp = requests.get(url, params=payload,
                                    headers=headers, timeout=timeout)
            else:
                resp = requests.post(
                    url, json=payload, headers=headers, timeout=timeout)

            resp.raise_for_status()
            return parser(resp.json())

        except (requests.RequestException, KeyError, ValueError):
            # graceful fallback to local default
            return default_email_strategy(registration_number, domain)

    return api_strategy


# ── Generator class ───────────────────────────────────────────────────────────

class SchoolEmailGenerator:
    """
    Generates institutional email addresses from registration numbers.

    settings.py options:

        SCHOOL_EMAIL_DOMAIN   = 'institution.ac.ke'

        # local strategy key:
        SCHOOL_EMAIL_STRATEGY = 'default'

        # OR API config dict:
        SCHOOL_EMAIL_STRATEGY = {
            "url":    "https://api.myschool.ac.ke/generate-email/",
            "method": "POST",
            "headers": {"Authorization": "Bearer <token>"},
            "payload_builder": None,   # uses default
            "response_parser": None,   # uses default (expects {"email": "..."})
            "timeout": 5,
        }
    """

    BUILT_IN_STRATEGIES = {
        'default':       default_email_strategy,
        'initials_year': initials_year_strategy,
        'numeric_only':  numeric_only_strategy,
    }

    def __init__(self, domain: Optional[str] = None, strategy: Optional[Callable] = None):
        self.domain = domain or getattr(
            settings, 'SCHOOL_EMAIL_DOMAIN', 'institution.com')
        self.strategy = strategy or self._resolve_strategy()

    def _resolve_strategy(self) -> Callable:
        setting = getattr(settings, 'SCHOOL_EMAIL_STRATEGY', 'default')

        # dict → build an API strategy
        if isinstance(setting, dict):
            return make_api_strategy(
                url=setting["url"],
                method=setting.get("method", "POST"),
                payload_builder=setting.get("payload_builder"),
                response_parser=setting.get("response_parser"),
                headers=setting.get("headers"),
                timeout=setting.get("timeout", 5),
            )

        # string key or dotted import path
        if isinstance(setting, str):
            if setting in self.BUILT_IN_STRATEGIES:
                return self.BUILT_IN_STRATEGIES[setting]
            try:
                from django.utils.module_loading import import_string
                return import_string(setting)
            except ImportError:
                return default_email_strategy

        if callable(setting):
            return setting

        return default_email_strategy

    def generate(self, registration_number: str) -> str:
        return self.strategy(registration_number, self.domain)

    def is_unique(self, email: str) -> bool:
        from base.models import Student
        return not Student.objects.filter(school_email=email).exists()

    def generate_unique(self, registration_number: str) -> str:
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
