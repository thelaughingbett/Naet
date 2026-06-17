# management/commands/import_results.py

from django.core.management.base import BaseCommand
from base.models import Session
from base.modules.results.service import run_results_import, get_strategy


class Command(BaseCommand):
    help = 'Import results for a session using the configured strategy'

    def add_arguments(self, parser):
        parser.add_argument('--session', type=str,
                            help='Session record_id (defaults to active)')
        parser.add_argument('--file',    type=str,
                            help='Path to Excel file (for Excel strategy)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Validate without writing to DB')

    def handle(self, *args, **options):
        session = (
            Session.objects.filter(record_id=options['session']).first()
            if options['session']
            else Session.objects.filter(is_active=True).first()
        )

        if not session:
            self.stderr.write("No active session found.")
            return

        strategy = get_strategy()
        self.stdout.write(f"Strategy: {strategy.__class__.__name__}")
        self.stdout.write(f"Session:  {session}")

        kwargs = {}
        if options.get('file'):
            kwargs['path'] = options['file']

        if options['dry_run']:
            result = strategy.load(session, **kwargs)
            errors = strategy.validate(result)

            if not result.success:
                self.stderr.write(self.style.ERROR(f"❌ {result.message}"))
                return

            for w in result.warnings:
                self.stdout.write(f"  ⚠  {w}")

            if errors:
                for e in errors:
                    self.stderr.write(f"  ✗ {e}")
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Dry run OK — {len(result.entries)} entries, no errors."
                ))
            return

        success, message, count = run_results_import(session, **kwargs)

        if success:
            self.stdout.write(self.style.SUCCESS(f"✅ {message}"))
        else:
            self.stderr.write(self.style.ERROR(f"❌ {message}"))
