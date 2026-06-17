from base.modules.results.base import (
    AbstractResultsStrategy,
    ResultEntry,
    ResultImportResult,
)


class ExcelResultsStrategy(AbstractResultsStrategy):
    """
    Imports results from an Excel file.

    Expected columns (order matters, header row required):
        registration_number | course_code | result_type | score | title

    result_type must be 'C' (CAT) or 'E' (Exam).

    Usage:
        strategy = ExcelResultsStrategy()
        result   = strategy.load(session, source=open_file_object)
        # or
        result   = strategy.load(session, path='/srv/uploads/results.xlsx')

    Settings (optional):
        RESULTS_EXCEL_SHEET = 0        # sheet index or name, default first sheet
        RESULTS_EXCEL_HEADER_ROW = 1   # 1-indexed row where headers are, default 1
    """

    def load(self, session, **kwargs) -> ResultImportResult:
        try:
            import openpyxl
        except ImportError:
            return ResultImportResult(
                success=False,
                message="openpyxl not installed. Run: pip install openpyxl"
            )

        from django.conf import settings as django_settings

        sheet_index = getattr(django_settings, 'RESULTS_EXCEL_SHEET', 0)
        header_row = getattr(django_settings, 'RESULTS_EXCEL_HEADER_ROW', 1)

        # accept either a file object or a path
        source = kwargs.get('source') or kwargs.get('path')
        if not source:
            return ResultImportResult(
                success=False,
                message="No source provided. Pass source=file_object or path='/path/to/file.xlsx'"
            )

        try:
            wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
            ws = wb.worksheets[sheet_index] if isinstance(
                sheet_index, int) else wb[sheet_index]
            rows = list(ws.iter_rows(min_row=header_row + 1, values_only=True))
        except Exception as e:
            return ResultImportResult(
                success=False,
                message=f"Could not read Excel file: {e}"
            )

        entries = []
        warnings = []

        for i, row in enumerate(rows, start=header_row + 1):
            if not any(row):
                continue  # skip blank rows

            try:
                reg_no, course_code, result_type, score, title = row[:5]
            except (TypeError, ValueError):
                warnings.append(f"Row {i}: could not unpack — skipped")
                continue

            # coerce and clean
            reg_no = str(reg_no).strip() if reg_no else ''
            course_code = str(course_code).strip(
            ).upper() if course_code else ''
            result_type = str(result_type).strip(
            ).upper() if result_type else ''
            title = str(title).strip() if title else ''

            try:
                score = float(score)
            except (TypeError, ValueError):
                warnings.append(
                    f"Row {i}: score '{score}' is not a number — skipped")
                continue

            if not reg_no or not course_code:
                warnings.append(
                    f"Row {i}: missing registration_number or course_code — skipped")
                continue

            entries.append(ResultEntry(
                registration_number=reg_no,
                course_code=course_code,
                result_type=result_type,
                score=score,
                title=title,
                meta={'row': i},
            ))

        return ResultImportResult(
            success=True,
            entries=entries,
            warnings=warnings,
            message=f"Read {len(entries)} entries from Excel.",
            stats={
                'rows_read':    len(rows),
                'rows_parsed':  len(entries),
                'rows_skipped': len(warnings),
                'source':       str(source) if isinstance(source, str) else getattr(source, 'name', 'upload'),
            }
        )
