from django.core.management.base import BaseCommand
from base.models import Venue, Building


class Command(BaseCommand):
    def handle(self, *args, **options):
        NS_BUILDING, _ = Building.objects.get_or_create(
            building_name='New Site',
            building_code='NS',
            total_floors=1
        )

        for i in range(1, 13):
            floor = 0
            if i > 6:
                floor = 1

            Venue.objects.get_or_create(
                capacity=120,
                venue_name=f"NS-{i}",
                building=NS_BUILDING,
                floor=floor
            )

        MTELO_LECTURE_HALL, _ = Building.objects.get_or_create(
            building_name='Mtelo Lecture Hall',
            building_code='LH',
            total_floors=1
        )

        for i in range(1, 7):
            Venue.objects.get_or_create(
                capacity=100,
                venue_name=f"LH-{i}",
                building=MTELO_LECTURE_HALL,
            )

        ED_COMPLEX, _ = Building.objects.get_or_create(
            building_name='School of Education Complex',
            building_code='ED',
            total_floors=2
        )

        for i in range(1, 21):
            floor = 0

            if i > 12:
                floor = 2
            elif i > 6:
                floor = 1

            Venue.objects.get_or_create(
                capacity=100,
                venue_name=f"ED-{i}",
                building=ED_COMPLEX,
                floor=floor
            )
