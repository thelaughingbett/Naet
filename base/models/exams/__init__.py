# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Exams subpackage — the exam department's side of the schema:

- exam_papers.py       QuestionPaper, QuestionPaperModeration,
                        QuestionBankItem — setting/moderating the
                        paper sat for an ExamSession.
- attendance.py        ExamAttendance — whether a student sat an
                        ExamSession, and any malpractice reported.
- academic_records.py  GradeCard, RevaluationRequest,
                        BacklogRegistration — downstream processing
                        of published results (term rollups, disputes,
                        re-sits).
- registrar.py         TranscriptRequest, Certificate — official
                        documents the registrar issues to a student.
"""

from .exam_papers import (
    QuestionPaper,
    QuestionPaperModeration,
    QuestionBankItem,
)
from .attendance import (
    ExamAttendance,
)
from .academic_records import (
    GradeCard,
    RevaluationRequest,
    BacklogRegistration,
)
from .registrar import (
    TranscriptRequest,
    Certificate,
)

__all__ = [
    "QuestionPaper",
    "QuestionPaperModeration",
    "QuestionBankItem",
    "ExamAttendance",
    "GradeCard",
    "RevaluationRequest",
    "BacklogRegistration",
    "TranscriptRequest",
    "Certificate",
]
