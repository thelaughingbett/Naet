# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/council/'s contents, split along the section
boundaries the original file already marked with comment dividers:
positions.py (shared vocab + CouncilTerm + CouncilPosition),
elections.py (Election, ElectionPosition, Candidate, Vote),
proposals.py (CouncilProposal, ProposalSupport), grievances.py
(Grievance, GrievanceUpdate), meetings.py (CouncilMeeting,
CouncilMeetingAttendance).

elections.py imports CouncilPosition directly (not just by string FK)
because Election.declare_winners() calls CouncilPosition.objects.create()
and .filter() — that's a real Python-level cross-file dependency, not
just Django's usual lazy string-reference resolution.
"""

from .positions import (  # noqa: F401
    COUNCIL_POSITION_CHOICES,
    EXECUTIVE_POSITIONS,
    CouncilTerm,
    CouncilPosition,
)
from .elections import (  # noqa: F401
    Election,
    ElectionPosition,
    Candidate,
    Vote,
)
from .proposals import (  # noqa: F401
    CouncilProposal,
    ProposalSupport,
)
from .grievances import (  # noqa: F401
    Grievance,
    GrievanceUpdate,
)
from .meetings import (  # noqa: F401
    CouncilMeeting,
    CouncilMeetingAttendance,
)

__all__ = [
    'COUNCIL_POSITION_CHOICES', 'EXECUTIVE_POSITIONS',
    'CouncilTerm', 'CouncilPosition',
    'Election', 'ElectionPosition', 'Candidate', 'Vote',
    'CouncilProposal', 'ProposalSupport',
    'Grievance', 'GrievanceUpdate',
    'CouncilMeeting', 'CouncilMeetingAttendance',
]
