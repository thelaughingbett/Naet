# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/clubs/'s contents: club identity + staff
oversight (club.py), student membership/leadership/recruitment
(membership.py), events + attendance (events.py), finance
(finance.py), and periodic reporting (reports.py).

Split rationale: unlike academics/ (one indivisible structural
hierarchy), clubs.py bundled five workflows with genuinely different
stakeholders — patrons oversee the club, exec members run membership,
a treasurer runs finance, the Dean's office approves events/reports.
That's closer to the adminstration/ precedent (sibling business
processes sharing a parent record) than to academics/'s single chain,
so five files instead of a light 3-4 file grouping.

Only one cross-file Python import was actually needed:
ClubLeadershipPosition.clubs_administered_by() (membership.py) returns
a real Club queryset, not just a related-manager lookup, so it imports
Club directly from club.py. Everything else references sibling models
only via Django's string FK syntax or related-name managers, which
Django resolves lazily — no import ordering concerns there.
"""

from .club import Club, ClubPatron  # noqa: F401
from .membership import (  # noqa: F401
    ClubMembership,
    ClubLeadershipPosition,
    ClubRecruitmentDrive,
)
from .events import ClubEvent, ClubEventAttendance  # noqa: F401
from .finance import ClubBudget, ClubTransaction  # noqa: F401
from .reports import ClubActivityReport  # noqa: F401

__all__ = [
    'Club',
    'ClubPatron',
    'ClubMembership',
    'ClubLeadershipPosition',
    'ClubRecruitmentDrive',
    'ClubEvent',
    'ClubEventAttendance',
    'ClubBudget',
    'ClubTransaction',
    'ClubActivityReport',
]
