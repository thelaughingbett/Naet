from django.core.management.base import BaseCommand
from base.models import Venue


class Command(BaseCommand):
    def handle(self, *args, **options):
        for i in range(1, 13):
            Venue.objects.get_or_create(
                capacity=120,
                venue_name=f"NS-{i}"
            )

        for i in range(1, 7):
            Venue.objects.get_or_create(
                capacity=100,
                venue_name=f"LH-{i}"
            )
