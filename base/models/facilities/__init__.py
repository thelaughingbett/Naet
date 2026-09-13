# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Facilities subpackage — the physical campus:

- facilities.py      Building, Venue — structures and the individual
                      rooms/halls/labs inside them.
- hostel.py           Hostel, Room, HostelAllocation — on-campus
                      student housing and room allocation.
- hostel_listing.py   HostelListing — off-campus hostel guide entries
                      for the student housing guide; independent of
                      the on-campus Hostel model above.
"""

from .base import (
    Building,
    Venue,
)
from .hostel import (
    Hostel,
    Room,
    HostelAllocation,
)
from .hostel_listing import (
    HostelListing,
)

__all__ = [
    "Building",
    "Venue",
    "Hostel",
    "Room",
    "HostelAllocation",
    "HostelListing",
]
