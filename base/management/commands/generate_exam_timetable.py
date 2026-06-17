# management/commands/generate_exam_timetable.py

from django.core.management.base import BaseCommand
from base.models import Session
from base.utils.timetable.exam_timetable_generator import generate_exam_timetable

# python manage.py generate_exam_timetable              # MAIN exams, active session
# python manage.py generate_exam_timetable - -type CAT   # CAT exams
# python manage.py generate_exam_timetable - -type SUPP - -session < uuid >


class Command(BaseCommand):
    help = 'Generate exam timetable for the active session'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='MAIN',
            choices=['CAT', 'MAIN', 'SUPP'],
            help='Exam type to generate (default: MAIN)'
        )
        parser.add_argument(
            '--session',
            type=str,
            help='Session record_id (defaults to active session)'
        )

    def handle(self, *args, **options):
        exam_type = options['type']

        if options['session']:
            session = Session.objects.filter(
                record_id=options['session']
            ).first()
            if not session:
                self.stderr.write(f"Session not found.")
                return
        else:
            session = Session.objects.filter(is_active=True).first()

        if not session:
            self.stderr.write("No active session found.")
            return

        self.stdout.write(f"Generating {exam_type} exams for {session}...")

        try:
            count = generate_exam_timetable(session, exam_type=exam_type)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Generated {count} exam sessions for {session}."
                )
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ {e}"))
