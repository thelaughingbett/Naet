# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/curriculum/'s three files as one namespace:
curriculum.py (Syllabus, Curriculum, LecturerAssignment,
CommonUnitCurriculum — already exists, contents assumed unchanged),
enrollment.py (Enrollment — already exists, contents assumed
unchanged), and grading_policy.py (GradingScale, GradingBand,
WeightingScheme, WeightingComponent — new, delivered alongside this file).

I haven't seen curriculum.py's or enrollment.py's current contents in
this split form, only the pre-split version (a single file covering
Syllabus/Curriculum/LecturerAssignment/CommonUnitCurriculum/Enrollment/
Result together). The import lines below assume curriculum.py kept the
first four and enrollment.py took Enrollment — adjust the class names
on the right of each import if that split landed differently.
"""

from .curriculum import (  # noqa: F401
    ASSIGNMENT_STATUS_CHOICES,
    Syllabus,
    Curriculum,
    LecturerAssignment,
    CommonUnitCurriculum,
)
from .enrollment import (
    Enrollment,
    Result
)  # noqa: F401
from .grading_policy import (  # noqa: F401
    RESULT_TYPE_CHOICES,
    GradingScale,
    GradingBand,
    WeightingScheme,
    WeightingComponent,
)

__all__ = [
    'ASSIGNMENT_STATUS_CHOICES',
    'Syllabus',
    'Curriculum',
    'LecturerAssignment',
    'CommonUnitCurriculum',
    'Enrollment',
    'Result',
    'RESULT_TYPE_CHOICES',
    'GradingScale',
    'GradingBand',
    'WeightingScheme',
    'WeightingComponent',
]
