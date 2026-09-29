from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from base.models import Enrollment


class Command(BaseCommand):
    help = "One-off: finalize any enrollment whose weighting components are complete but graded_at is still unset."

    def handle(self, *args, **options):
        candidates = list(Enrollment.objects.filter(graded_at__isnull=True))
        total = len(candidates)
        finalized = 0
        skipped = 0

        for enr in candidates:
            try:
                if enr.finalize_grade():
                    finalized += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Finalized {enr} — score {enr.graded_score}, "
                        f"{enr.grade_points_earned} pts, "
                        f"{'passed' if enr.graded_score >= enr.pass_mark_applied else 'failed'}"
                    ))
                # finalize_grade() returning False (not enough submissions
                # yet) is expected and not worth a line per enrollment —
                # only actual finalizations and actual errors get printed.
            except ValidationError as e:
                skipped += 1
                self.stderr.write(self.style.ERROR(f"Skipped {enr}: {e}"))

        self.stdout.write(
            f"\nFinalized {finalized} of {total} candidates "
            f"({skipped} skipped due to errors, "
            f"{total - finalized - skipped} not yet complete)."
        )
