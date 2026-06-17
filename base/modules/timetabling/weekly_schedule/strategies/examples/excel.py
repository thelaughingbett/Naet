from base.modules.timetabling.weekly_schedule.base import (
    AbstractTimetableStrategy,
    TimetableGenerationResult,
    TimetableSlot,
)
from base.models import Curriculum, Venue
from django.conf import settings


class ExcelImportStrategy(AbstractTimetableStrategy):
    """
    Reads a timetable from an Excel file instead of generating one.

    The Excel file must have columns:
        course_code | class_name | day | time_slot | venue_name

    Settings required:
        TIMETABLE_EXCEL_PATH = '/path/to/timetable.xlsx'
    """

    def generate(self, session) -> TimetableGenerationResult:
        try:
            import openpyxl
        except ImportError:
            return TimetableGenerationResult(
                success=False,
                message="openpyxl not installed. Run: pip install openpyxl"
            )

        path = getattr(settings, 'TIMETABLE_EXCEL_PATH', None)
        if not path:
            return TimetableGenerationResult(
                success=False,
                message="TIMETABLE_EXCEL_PATH not set in settings."
            )

        try:
            wb = openpyxl.load_workbook(path)
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
        except Exception as e:
            return TimetableGenerationResult(success=False, message=f"Could not read Excel: {e}")

        # build lookups
        curriculum_map = {
            (c.course.course_code, c.Tclass.class_name): str(c.record_id)
            for c in Curriculum.objects.filter(session=session)
            .select_related('course', 'Tclass')
        }
        venue_map = {
            v.venue_name: str(v.record_id)
            for v in Venue.objects.all()
        }

        slots = []
        warnings = []

        for i, row in enumerate(rows, start=2):
            course_code, class_name, day, time_slot, venue_name = row

            curriculum_id = curriculum_map.get((course_code, class_name))
            if not curriculum_id:
                warnings.append(
                    f"Row {i}: {course_code}/{class_name} not in session — skipped")
                continue

            venue_id = venue_map.get(venue_name)
            if not venue_id:
                warnings.append(
                    f"Row {i}: venue '{venue_name}' not found — skipped")
                continue

            slots.append(TimetableSlot(
                curriculum_id=curriculum_id,
                day=day,
                time_slot=time_slot,
                venue_id=venue_id,
            ))

        return TimetableGenerationResult(
            success=True,
            slots=slots,
            warnings=warnings,
            message=f"Imported {len(slots)} slots from Excel.",
        )
