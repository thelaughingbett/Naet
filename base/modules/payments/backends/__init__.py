"""
Payments Backend Module & Registry System

This module implements an open, pluggable architecture for payment gateways. 
Every payment provider must inherit from `AbstractPaymentBackend` and register 
its instance with the system's global backend registry.


Folder Structure Reference:
    payments/
    ├── backends/            <-- Pure directory layout
    │   ├── contrib/             
    │   │   └── backends/    <-- Community Open-Source Contributions Go Here
    │   ├── example/             
    │   │   ├── backends.equity.example.py
    │   │   └── backends.mpesa.example.py
    │   ├── __init__.py      # This file (handles initialization)
    │   └── base.py          # Contains AbstractPaymentBackend and dataclasses
    ├── registry.py          # Central registry engine
    ├── services.py          # Business logic processing ledger rules
    ├── urls.py              # Centralized webhook routing endpoints
    └── views.py             # Global webhook receiving controller

Where to Write Your Custom Backend:

    1. Local Integrator / Corporate Setup:
       Write your gateway module directly inside the core `payments/backends/` 
       directory alongside `base.py`.
       
    2. Open-Source Contributor Setup:
       Write your vendor-specific gateway module inside the `payments/contrib/backends/` 
       directory to keep the core code footprint clean and maintainable.

Registration Patterns:

    Pattern A: Static Registration (Core / Integrator / Contributor Modules)
    ------------------------------------------------------------------------
    Import and register your backend instance explicitly inside the initialization 
    sequence of your application startup hook, or directly in this init package:

        from payments.registry import payment_registry
        from payments.backends.equity import EquityBankBackend
        from payments.contrib.backends.kcb import KCBPaymentBackend

        payment_registry.register(EquityBankBackend())
        payment_registry.register(KCBPaymentBackend())

    Pattern B: Dynamic Integration (Third-Party Isolated Django Apps)
    ------------------------------------------------------------------
    If your backend lives in a detached third-party module app, register it via 
    Django's Application Configuration startup hook:

        # outside_app/apps.py
        from django.apps import AppConfig

        class OutsideAppConfig(AppConfig):
            name = 'outside_app'

            def ready(self):
                from payments.registry import payment_registry
                from .backends import CustomGatewayBackend
                
                payment_registry.register(CustomGatewayBackend())

Execution Flow Contract:
    - Custom backends must NEVER modify database records inside `initiate()` or `verify_webhook()`.
    - Always yield standard `PaymentInitiationResult` or `WebhookVerificationResult` data structures.
    - Financial balance updates, ledger logging, and notifications are securely handled by core.
"""

from .base import (
    AbstractPaymentBackend,
    PaymentInitiationResult,
    WebhookVerificationResult,
    FormField,
    PaymentFormConfig
)


__all__ = [
    'AbstractPaymentBackend',
    'PaymentInitiationResult',
    'WebhookVerificationResult',
    'FormField',
    'PaymentFormConfig'
]
