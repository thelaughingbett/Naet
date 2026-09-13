# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports everything from the split model modules so the rest of the
app can keep doing `from base.models import Complaint` (or `Graduation`,
`Deferment`, etc.) unchanged — nothing outside base/models/ needs to
know these classes live in separate files now.

Import order matters a little here: modules with no cross-file model
references (base, hostel_listing, reporting) first, then modules that
reference each other only by Django's lazy 'AppLabel' / string FK
syntax (e.g. models.ForeignKey('Complaint', ...)) — those don't
actually need Python-level import ordering since Django resolves
string references at app-registry-ready time, not at import time. The
order below is for human readability, not correctness.

Adjust the filenames on the left of each `from .X import` if your
existing curriculum/university model files use different names than
assumed here — I don't have their real filenames, only their contents
from earlier in this conversation, so `curriculum` and `university`
below are best guesses, not confirmed paths.
"""

# --- Student lifecycle events -----------------------------------------
from .deferment import (  # noqa: F401
    DefermentDocument,
    Deferment,
)
from .reporting import Reporting  # noqa: F401
from .status_change import StatusChangeRequest  # noqa: F401

# --- Grievances / complaints --------------------------------------------
from .complaints import (  # noqa: F401
    COMPLAINT_CATEGORY_CHOICES,
    PRIORITY_CHOICES,
    STATUS_CHOICES,
    UPLOAD_ROLE_CHOICES,
    LEVEL_CHOICES,
    ESCALATION_PATHS,
    SLA_HOURS_BY_CATEGORY,
    PRIORITY_ORDER,
    get_sla_hours,
    ComplaintDocument,
    Complaint,
    ComplaintEscalationHistory,
)

# --- Graduation pipeline --------------------------------------------------
from .graduation import (  # noqa: F401
    CLASSIFICATION_CHOICES,
    DegreeAudit,
    Graduation,
    Diploma,
    Convocation,
)

# --- Evaluation -----------------------------------------------------------
from .evaluations import (
    CourseEvaluation,
    LecturerEvaluation,
    HostelEvaluation,
    HOSTEL_EVALUATION_CATEGORIES
)


# --- Admissions -------------------------------------------------------------

from .admissions import (
    Application,
    ApplicationDocument,
    TransferCreditEvaluation
)


__all__ = [
    # deferment / reporting / status change
    'DefermentDocument',
    'Deferment',
    'Reporting',
    'StatusChangeRequest',

    # complaints
    'COMPLAINT_CATEGORY_CHOICES',
    'PRIORITY_CHOICES',
    'STATUS_CHOICES',
    'UPLOAD_ROLE_CHOICES',
    'LEVEL_CHOICES',
    'ESCALATION_PATHS',
    'SLA_HOURS_BY_CATEGORY',
    'PRIORITY_ORDER',
    'get_sla_hours',
    'ComplaintDocument',
    'Complaint',
    'ComplaintEscalationHistory',

    # graduation
    'CLASSIFICATION_CHOICES',
    'DegreeAudit',
    'Graduation',
    'Diploma',
    'Convocation',


    # Evaluations
    'CourseEvaluation',
    'LecturerEvaluation',
    'HostelEvaluation',
    'HOSTEL_EVALUATION_CATEGORIES',

    # Admisssions
    'Application',
    'ApplicationDocument',
    'TransferCreditEvaluation',

]
