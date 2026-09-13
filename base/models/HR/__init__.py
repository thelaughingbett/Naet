# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
HR subpackage — staff-facing processes, as distinct from `staff/`
(which defines *what kind* of staff member someone is). Nothing here
cares whether the person is a Lecturer, AdministrativeStaff, ItStaff,
etc. — appraisal hangs off Lecturer specifically (it's a teaching/
research/service review), while leave hangs off the generic `User`
since every staff type takes leave the same way.

- appraisal.py   RatingScale, RATING_TO_SCORE, AppraisalCycle,
                 PerformanceAppraisal, AppraisalGoal,
                 AppraisalDocument — the lecturer performance-review
                 cycle: self-assessment -> HOD review -> Dean approval.
- leave.py       LeaveType, LeaveBalance, LeaveRequest,
                 LeaveApprovalStep, LeaveRequestDocument — leave
                 application, multi-step approval, and balance
                 tracking for any staff member.
"""

from .appraisal import (
    RatingScale,
    RATING_TO_SCORE,
    AppraisalCycle,
    PerformanceAppraisal,
    AppraisalGoal,
    AppraisalDocument,
)
from .leave import (
    LeaveType,
    LeaveBalance,
    LeaveRequest,
    LeaveApprovalStep,
    LeaveRequestDocument,
)

__all__ = [
    "RatingScale",
    "RATING_TO_SCORE",
    "AppraisalCycle",
    "PerformanceAppraisal",
    "AppraisalGoal",
    "AppraisalDocument",
    "LeaveType",
    "LeaveBalance",
    "LeaveRequest",
    "LeaveApprovalStep",
    "LeaveRequestDocument",
]
