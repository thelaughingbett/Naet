import json
from base.modules.results.base import (
    AbstractResultsStrategy,
    ResultEntry,
    ResultImportResult,
)


class LMSPushStrategy(AbstractResultsStrategy):
    """
    Accepts results pushed from an LMS (Moodle, Canvas, etc.)
    via the REST API endpoint POST /api/results/

    The LMS sends JSON:
    {
        "results": [
            {
                "registration_number": "CS/001/2024",
                "course_code": "CSC411",
                "result_type": "E",
                "score": 72.5,
                "title": "Final Exam"
            },
            ...
        ]
    }

    Usage (in the API view):
        strategy = LMSPushStrategy()
        result   = strategy.load(session, payload=request.data)
    """

    def load(self, session, **kwargs) -> ResultImportResult:
        payload = kwargs.get('payload')

        if not payload:
            return ResultImportResult(
                success=False,
                message="No payload provided. Pass payload=request.data"
            )

        try:
            raw_results = payload.get('results', [])
            if not isinstance(raw_results, list):
                return ResultImportResult(
                    success=False,
                    message="'results' must be a list."
                )
        except Exception as e:
            return ResultImportResult(success=False, message=str(e))

        entries = []
        warnings = []

        for i, item in enumerate(raw_results):
            try:
                entries.append(ResultEntry(
                    registration_number=str(
                        item['registration_number']).strip(),
                    course_code=str(item['course_code']).strip().upper(),
                    result_type=str(item['result_type']).strip().upper(),
                    score=float(item['score']),
                    title=str(item['title']).strip(),
                ))
            except (KeyError, ValueError, TypeError) as e:
                warnings.append(f"Item {i}: {e} — skipped")
                continue

        return ResultImportResult(
            success=True,
            entries=entries,
            warnings=warnings,
            message=f"Parsed {len(entries)} results from LMS payload.",
            stats={'items_received': len(
                raw_results), 'items_parsed': len(entries)},
        )
