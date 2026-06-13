"""
ERP Sync Tasks Module & Pluggable Handler Subsystem

This module establishes a generic, asynchronous pipeline for streaming data 
changes out to external Enterprise Resource Planning (ERP) engines using Celery. 
Handlers subclass `AbstractERPTask` and register with the global ERP registry.

Folder Structure Reference:
    erp/
    ├── tasks/                <-- Standard Core / Integrator tasks Go Here
    │   ├── __init__.py      # This file (package initialization & configuration)
    │   ├── base.py          # Abstract base classes and data contract models
    │   ├── contrib/         
    │   │   └── tasks/       <-- Community open-source external ERP wrappers go here 
    │   └── examples/        
    │       └── implementations.py # Sample blueprints for implementation reference
    ├── registry.py          # Event-routing mapping repository engine
    ├── dispatch.py          # Real-time event signal interception triggers
    └── models.py            # Audit trail record logging tables (ERPSyncLog)

Where to Write Your ERP Sync Handlers:

    1. Native Core Implementations:
       Write critical, campus-wide infrastructure tracking pipelines directly inside 
       the root `erp/tasks/` package namespace folder.
       
    2. Open-Source Contributions:
       Place targeted platform sync modules (e.g., SAP, Oracle, Sage, Odoo integrations) 
       cleanly into the `erp/tasks/contrib/tasks/` directory path.

Registration Patterns:

    Pattern A: Explicit Startup Mapping (Recommended)
    -------------------------------------------------
    Import and register handler definitions dynamically within your platform application 
    startup initialization file hooks:

        from erp.registry import erp_registry
        from erp.tasks.payments import PaymentERPTask
        from erp.tasks.contrib.tasks.sap import SAPEnrollmentTask

        erp_registry.register(PaymentERPTask())
        erp_registry.register(SAPEnrollmentTask())

    Pattern B: Distributed App Config Discovery
    -------------------------------------------
    Hook external detached packages using standard Django Application configuration bindings:

        # outside_erp_app/apps.py
        from django.apps import AppConfig

        class OutsideERPConfig(AppConfig):
            name = 'outside_erp_app'

            def ready(self):
                from erp.registry import erp_registry
                from .tasks import CustomAccountingERPTask
                
                erp_registry.register(CustomAccountingERPTask())

Data Isolation Contract:
    - Never couple multiple handler retries together. The backend separates loops automatically.
    - Always wrap delivery response data frames inside the explicit `ERPSyncResult` dataclass wrapper.
    - Soft structural payload delivery failures should return a `success=False` outcome packet.
    - Unhandled runtime execution exceptions safely invoke exponential backoff retry task loops.
"""

from .base import *  # noqa : F401,E402
from .sync import *  # noqa : F401,E402
