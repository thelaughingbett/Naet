# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResultEntry:
    """
    The normalised shape of one result record.

    Every strategy returns a list of these.
    Naet maps them to Result model instances — the strategy
    never touches the DB directly.

    registration_number:  identifies the student
    course_code:          identifies the curriculum entry
    result_type:          'C' (CAT) or 'E' (Exam) — must match Result.type_result
    score:                decimal, e.g. 68.50
    title:                label for this specific result e.g. 'CAT 1', 'Final Exam'
    """
    registration_number: str
    course_code:         str
    result_type:         str    # 'C' | 'E'
    score:               float
    title:               str

    # anything the strategy wants to attach for debugging
    meta: Optional[dict] = None


@dataclass
class ResultImportResult:
    """
    Returned by every strategy after attempting to import results.

    success:   False means nothing was written — caller should not proceed
    entries:   the proposed results — written to DB by Naet after validation
    message:   human-readable summary or error
    warnings:  non-fatal issues the caller should know about
               e.g. ["REG/001/2024 not found — skipped", "Score 105 clamped to 100"]
    stats:     optional metadata from the strategy
               e.g. {"rows_read": 120, "rows_skipped": 3, "source_file": "results.xlsx"}
    """
    success:  bool
    entries:  list[ResultEntry] = field(default_factory=list)
    message:  str = ""
    warnings: list[str] = field(default_factory=list)
    stats:    Optional[dict] = None


class AbstractResultsStrategy(ABC):
    """
    Contract every results import strategy must implement.

    Strategies are function-like objects — they receive a session
    and optional kwargs, return a ResultImportResult, and touch
    nothing in the DB.

    Everything else — resolving student/curriculum FKs, deduplication,
    bulk-creating Result records, handling transactions — is done by
    the core service after the strategy returns.

    ---

    How to register your strategy in settings.py:

        RESULTS_STRATEGY = 'base.modules.results.strategies.excel.ExcelResultsStrategy'

    How the core loads it:

        from django.utils.module_loading import import_string
        strategy_class = import_string(settings.RESULTS_STRATEGY)
        strategy = strategy_class()
        result = strategy.load(session, source=request.FILES['file'])

    ---

    Implementors must follow these rules:

    1. NEVER write to the DB inside load()
       Return ResultEntry objects — let Naet write them.

    2. ALWAYS catch your own exceptions
       Return ResultImportResult(success=False, message=str(e))
       Never let an exception propagate out of load().

    3. Use warnings for skippable rows — not errors
       A missing student or unrecognised course code is a warning.
       A completely unreadable file is an error (success=False).

    4. Never clamp or silently modify scores
       If a score is out of range, add a warning and include it as-is.
       Let the validator or the caller decide what to do with it.
    """

    @abstractmethod
    def load(self, session, **kwargs) -> ResultImportResult:
        """
        Load results for the given session from wherever this strategy reads from.

        session:  a Session model instance
        kwargs:   strategy-specific — e.g. source=file_object, path='/path/to/file.xlsx'

        Must return a ResultImportResult regardless of what happens.
        Must not raise.
        """
        raise NotImplementedError

    def validate(self, result: ResultImportResult) -> list[str]:
        """
        Validate the entries in a result before Naet writes them.

        Returns a list of error strings. Empty list = all good.

        Override to add strategy-specific validation on top of the
        base checks here.
        """
        valid_types = {'C', 'E'}
        errors = []

        for i, entry in enumerate(result.entries):
            if not entry.registration_number:
                errors.append(f"Entry {i}: registration_number is empty")
            if not entry.course_code:
                errors.append(f"Entry {i}: course_code is empty")
            if entry.result_type not in valid_types:
                errors.append(
                    f"Entry {i}: invalid result_type '{entry.result_type}' — "
                    f"must be one of {valid_types}"
                )
            if not isinstance(entry.score, (int, float)):
                errors.append(
                    f"Entry {i}: score must be a number, got '{entry.score}'")
            if not entry.title:
                errors.append(f"Entry {i}: title is empty")

        return errors
