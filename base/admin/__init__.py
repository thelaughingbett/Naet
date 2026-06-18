# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.contrib import admin

from .academic import *    # noqa: F401, E402
from .curriculum import *  # noqa: F401, E402
from .finance import *     # noqa: F401, E402
from .hostel import *      # noqa: F401, E402
from .misc import *        # noqa: F401, E402
from .users import *       # noqa: F401, E402
from .timetabling import *       # noqa: F401, E402


admin.site.site_header = 'Naet Admin portal'
admin.site.site_title = 'Naet Admin portal'
admin.site.index_title = 'Welcome to the administration portal'


# passwords
# lecturer - email:lecturer@email.com - password@123!
# admin - email:admin@email.com - admin
