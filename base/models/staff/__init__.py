# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Staff subpackage — the HR/personnel side of the schema:

- staff_profile.py    StaffProfile — the abstract foundation every
                       concrete staff type below inherits.
- academic.py          Lecturer, AcademicAppointment — teaching staff
                       and their leadership appointments.
- administrative.py    AdministrativeStaff — academic-aligned admin
                       personnel (registrar, VC office, dept/school
                       admins).
- support.py           GeneralStaff, HostelWarden, ItStaff,
                       FinanceStaff, LabTechnicalStaff, MedicalStaff,
                       LibraryStaff — operational staff outside the
                       academic/admin split above.
"""

from .staff_profile import (
    StaffProfile,
)
from .academic import (
    APPOINTMENT_CHOICES,
    ROLE_CHOICES,
    Lecturer,
    AcademicAppointment,
)
from .administrative import (
    ADMIN_ROLE_CHOICES,
    AdministrativeStaff,
)
from .support import (
    GeneralStaff,
    HostelWarden,
    ItStaff,
    FinanceStaff,
    LabTechnicalStaff,
    MedicalStaff,
    LibraryStaff,
)

__all__ = [
    "StaffProfile",
    "APPOINTMENT_CHOICES",
    "ROLE_CHOICES",
    "Lecturer",
    "AcademicAppointment",
    "ADMIN_ROLE_CHOICES",
    "AdministrativeStaff",
    "GeneralStaff",
    "HostelWarden",
    "ItStaff",
    "FinanceStaff",
    "LabTechnicalStaff",
    "MedicalStaff",
    "LibraryStaff",
]
