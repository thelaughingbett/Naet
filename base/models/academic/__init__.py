# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/academics/'s contents: the ISCED reference
table, the org hierarchy (Institution, School, Department), the
programme structure (Programme, Tclass), Session, and Course.

Split rationale: this is one cohesive bounded context (the academic
structure everything else hangs off), so it's four files grouped by
genuine sub-concern rather than one-class-per-file — Programme and
Tclass stay together because they reference each other constantly,
same for Institution/School/Department as the org hierarchy. Only the
ISCED constant (a static lookup, not model logic) and Session (has its
own significant rollover business logic) earned standalone files.

Note the original file's `import os`, `import magic`, and
`from base.modules.regulatory import agency_registry` weren't used
anywhere in the classes it defined — dropped here as dead imports.
If they're actually used by a method that wasn't in what was shared,
they'll need re-adding to whichever file needs them.
"""

from .isced import UNESCO_ISCED_FIELDS  # noqa: F401
from .organization import Institution, School, Department  # noqa: F401
from .programme import Programme, Tclass  # noqa: F401
from .session import Session  # noqa: F401
from .course import Course  # noqa: F401

__all__ = [
    'UNESCO_ISCED_FIELDS',
    'Institution', 'School', 'Department',
    'Programme', 'Tclass',
    'Session',
    'Course',
]
