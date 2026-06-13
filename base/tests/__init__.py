# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

# ---------------------------------------------------------------------------
# Test suite for <app_name>
#
# Structure:
#   tests/
#   ├── __init__.py          ← this file
#   ├── test_models.py       ← unit tests for models (methods, properties, signals)
#   ├── test_views.py        ← view tests (status codes, context, redirects)
#   ├── test_forms.py        ← form validation tests
#   ├── test_admin.py        ← admin queryset scoping, actions, permissions
#   ├── test_signals.py      ← signal receiver tests
#   ├── test_tasks.py        ← celery task tests
#   └── factories.py         ← factory_boy model factories shared across tests
# ---------------------------------------------------------------------------

from .test_models import *   # noqa: F401
from .test_views import *    # noqa: F401
from .test_forms import *    # noqa: F401
from .test_admin import *    # noqa: F401
from .test_signals import *  # noqa: F401
from .test_tasks import *    # noqa: F401
