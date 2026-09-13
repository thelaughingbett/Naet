# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Compliance subpackage — regulatory/statutory obligations and the
deadlines they impose:

- accreditation.py         AccreditationDocument, Accreditation —
                            institutional/programme accreditation
                            status with an external regulatory body.
- registration_windows.py  RegistrationWindow — open/close periods
                            for course registration, bursary, hostel,
                            exams, graduation candidacy, and more.
- regulatory_reports.py    RegulatoryReportDocument, RegulatoryReport,
                            TRIGGER_CHOICES, STATUS_CHOICES,
                            REPORT_TYPE_CHOICES — statutory submissions
                            to a regulatory agency.
- calendar.py               ComplianceCalendarEvent, SOURCE_TYPE_CHOICES,
                            RECURRENCE_CHOICES — the denormalized
                            deadline rollup over the three files above.
"""

from .accreditation import (
    AccreditationDocument,
    Accreditation,
)
from .registration_windows import (
    RegistrationWindow,
)
from .regulatory_reports import (
    TRIGGER_CHOICES,
    STATUS_CHOICES,
    REPORT_TYPE_CHOICES,
    RegulatoryReportDocument,
    RegulatoryReport,
)
from .calendar import (
    SOURCE_TYPE_CHOICES,
    RECURRENCE_CHOICES,
    ComplianceCalendarEvent,
)

__all__ = [
    "AccreditationDocument",
    "Accreditation",
    "RegistrationWindow",
    "TRIGGER_CHOICES",
    "STATUS_CHOICES",
    "REPORT_TYPE_CHOICES",
    "RegulatoryReportDocument",
    "RegulatoryReport",
    "SOURCE_TYPE_CHOICES",
    "RECURRENCE_CHOICES",
    "ComplianceCalendarEvent",
]
