# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import BaseModelMixin
from django.db import models


class CourseEvaluation(BaseModelMixin):
    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(
        default=0
    )

    comments = models.TextField(
        blank=True,
        null=True
    )


class LecturerEvaluation(
    BaseModelMixin
):
    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.CASCADE
    )

    lecturer = models.ForeignKey(
        "Lecturer",
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(
        default=0
    )

    comments = models.TextField(
        blank=True,
        null=True
    )
