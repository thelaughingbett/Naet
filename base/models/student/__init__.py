# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/student/'s contents: the counties reference
table (reference.py), core Student identity + status proxies
(student.py), IDCard (id_card.py), and the medical/clinical records
that got isolated on trust-boundary grounds, not just size (medical.py).
"""

from .reference import KENYAN_COUNTIES  # noqa: F401
from .student import (  # noqa: F401
    Student,
    DeferredStudent,
    ResidentStudent,
    GraduatedStudent,
)
from .id_card import IDCard  # noqa: F401
from .medical import (  # noqa: F401
    BLOOD_GROUP_CHOICES,
    ENCOUNTER_TYPE_CHOICES,
    CLASSIFICATION_CHOICES,
    StudentMedicalProfile,
    ClinicEncounter,
)
from .contacts import (
    ParentGuardian,
    EmergencyContact
)
from .student_risk_score import (
    StudentRiskScore
)

__all__ = [
    'KENYAN_COUNTIES',
    'Student',
    'DeferredStudent',
    'ResidentStudent',
    'GraduatedStudent',
    'IDCard',
    'BLOOD_GROUP_CHOICES',
    'ENCOUNTER_TYPE_CHOICES',
    'CLASSIFICATION_CHOICES',
    'StudentMedicalProfile',
    'ClinicEncounter',
    'ParentGuardian',
    'EmergencyContact',
    'StudentRiskScore'
]
