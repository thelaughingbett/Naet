# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Re-exports base/models/innovation/'s contents, split along the section
boundaries the original file already marked with comment dividers:
ideation.py (Idea, IdeaReview, Mentor, MentorAssignment),
incubation.py (Cohort, Startup, Milestone, Resource, ResourceBooking),
funding.py (GrantScheme, GrantApplication, SeedFundDisbursement,
Investor), ip.py (InventionDisclosure, IPRecord, LicensingAgreement),
research.py (ResearchProject, Publication, IndustryCollaboration),
events.py (InnovationEvent, EventRegistration), partnerships.py
(IndustryPartner, MemorandumOfUnderstanding, AlumniEntrepreneur).

All cross-model references between these files use Django's string FK
syntax ('Idea', 'Startup', 'GrantApplication', ...), so import order
below is for readability, not correctness — unlike council/elections.py,
nothing here needs a direct Python-level import of another file's class.

Note: nothing in this whole domain uses HistoricalRecords — no model
here tracks change history, unlike Complaint/Graduation/CouncilPosition
elsewhere. Financial records (GrantApplication, SeedFundDisbursement)
and legal ones (IPRecord, LicensingAgreement, MemorandumOfUnderstanding)
seem like exactly the kind of thing you'd want an audit trail for, so
this is worth a second look — not something I've silently added here,
since adding history tracking is a real schema change (a migration per
model), not a refactor.
"""

from .ideation import (  # noqa: F401
    Idea,
    IdeaReview,
    Mentor,
    MentorAssignment,
)
from .incubation import (  # noqa: F401
    Cohort,
    Startup,
    Milestone,
    Resource,
    ResourceBooking,
)
from .funding import (  # noqa: F401
    GrantScheme,
    GrantApplication,
    SeedFundDisbursement,
    Investor,
)
from .ip import (  # noqa: F401
    InventionDisclosure,
    IPRecord,
    LicensingAgreement,
)
from .research import (  # noqa: F401
    ResearchProject,
    Publication,
    IndustryCollaboration,
)
from .events import (  # noqa: F401
    InnovationEvent,
    EventRegistration,
)
from .partnerships import (  # noqa: F401
    IndustryPartner,
    MemorandumOfUnderstanding,
    AlumniEntrepreneur,
)

__all__ = [
    'Idea', 'IdeaReview', 'Mentor', 'MentorAssignment',
    'Cohort', 'Startup', 'Milestone', 'Resource', 'ResourceBooking',
    'GrantScheme', 'GrantApplication', 'SeedFundDisbursement', 'Investor',
    'InventionDisclosure', 'IPRecord', 'LicensingAgreement',
    'ResearchProject', 'Publication', 'IndustryCollaboration',
    'InnovationEvent', 'EventRegistration',
    'IndustryPartner', 'MemorandumOfUnderstanding', 'AlumniEntrepreneur',
]
