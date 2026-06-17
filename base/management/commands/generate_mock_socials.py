"""
Management command: generate_mock_socials

Generates mock EventItem and NewsItem records for local development and
manual testing of the socials (events/news) pages.

Place this file at:
    base/management/commands/generate_mock_socials.py

(make sure base/management/__init__.py and
base/management/commands/__init__.py exist — Django won't discover the
command otherwise)

All records use external_id values prefixed with "mock-event-" or
"mock-news-", so --clear only ever touches data created by this command —
it will never delete real synced or manually-entered records.

Usage:
    python manage.py generate_mock_socials
    python manage.py generate_mock_socials --clear
    python manage.py generate_mock_socials --events-only
    python manage.py generate_mock_socials --news-only
    python manage.py generate_mock_socials --clear --news-only
"""

import datetime

from django.core.management.base import BaseCommand

from base.models import EventItem, NewsItem  # TODO: adjust import path


def _date(offset_days):
    """Today + offset_days, so the mock data always looks fresh whenever
    the command is run (negative offsets = past, 0 = today, positive = upcoming)."""
    return datetime.date.today() + datetime.timedelta(days=offset_days)


def _time(hour, minute=0):
    return datetime.time(hour=hour, minute=minute)


MOCK_EVENTS = [
    {
        "external_id": "mock-event-orientation",
        "title": "Orientation Week Welcome Party",
        "description": "Kick off the semester with games, music, and free food for new and returning students.",
        "category": "Social",
        "date": _date(-5),
        "start_time": _time(17, 0),
        "end_time": _time(21, 0),
        "location": "Student Centre Lawn",
        "is_online": False,
        "meeting_url": None,
        "badge": "🎊 Welcome",
        "thumbnail": "https://picsum.photos/seed/orientation/600/360",
        "source_url": "https://example.edu/events/orientation-week",
        "source_name": "Student Affairs Office",
        "rsvp_url": None,
        "rsvp_deadline": None,
    },
    {
        "external_id": "mock-event-open-day",
        "title": "Faculty Open Day",
        "description": "Departments showcase ongoing projects, research, and student work. Drop in any time.",
        "category": "Academic",
        "date": _date(0),
        "start_time": _time(9, 0),
        "end_time": _time(15, 0),
        "location": "Main Hall",
        "is_online": False,
        "meeting_url": None,
        "badge": "🔴 Today",
        "thumbnail": "https://picsum.photos/seed/openday/600/360",
        "source_url": "https://example.edu/events/open-day",
        "source_name": "Academic Affairs",
        "rsvp_url": None,
        "rsvp_deadline": None,
    },
    {
        "external_id": "mock-event-tech-symposium",
        "title": "Tech Symposium 2026",
        "description": "Annual tech expo featuring AI, cybersecurity, and industry panels. Open to all students.",
        "category": "Academic",
        "date": _date(3),
        "start_time": _time(9, 0),
        "end_time": _time(16, 0),
        "location": "Main Hall",
        "is_online": False,
        "meeting_url": None,
        "badge": "⭐ Featured",
        "thumbnail": "https://picsum.photos/seed/techsymposium/600/360",
        "source_url": "https://example.edu/events/tech-symposium-2026",
        "source_name": "Faculty of Computing",
        "rsvp_url": "https://example.edu/rsvp/tech-symposium-2026",
        "rsvp_deadline": _date(2),
    },
    {
        "external_id": "mock-event-cultural-fest",
        "title": "University Cultural Fest",
        "description": "Celebrate diversity with music, dance, and food from different cultures.",
        "category": "Cultural",
        "date": _date(8),
        "start_time": _time(14, 0),
        "end_time": _time(20, 0),
        "location": "Amphitheatre",
        "is_online": False,
        "meeting_url": None,
        "badge": "🎉 Annual",
        "thumbnail": "https://picsum.photos/seed/culturalfest/600/360",
        "source_url": "https://example.edu/events/cultural-fest",
        "source_name": "Student Council",
        "rsvp_url": "https://example.edu/rsvp/cultural-fest",
        "rsvp_deadline": _date(7),
    },
    {
        "external_id": "mock-event-football",
        "title": "Inter-Faculty Football Tournament",
        "description": "Cheer for your faculty! Group stages run all day, finals in the evening.",
        "category": "Sports",
        "date": _date(12),
        "start_time": _time(10, 0),
        "end_time": _time(17, 0),
        "location": "Sports Complex",
        "is_online": False,
        "meeting_url": None,
        "badge": "⚽",
        "thumbnail": "https://picsum.photos/seed/football/600/360",
        "source_url": "https://example.edu/events/football-tournament",
        "source_name": "Sports Department",
        "rsvp_url": "https://example.edu/rsvp/football-tournament",
        "rsvp_deadline": _date(10),
    },
    {
        "external_id": "mock-event-research-workshop",
        "title": "Research Writing Workshop",
        "description": "Learn how to write high-impact research papers and thesis proposals.",
        "category": "Workshop",
        "date": _date(20),
        "start_time": _time(10, 0),
        "end_time": _time(13, 0),
        "location": None,
        "is_online": True,
        "meeting_url": "https://zoom.us/j/1234567890",
        "badge": "📝 Certificate",
        "thumbnail": "https://picsum.photos/seed/researchworkshop/600/360",
        "source_url": "https://example.edu/events/research-writing-workshop",
        "source_name": "Postgraduate School",
        "rsvp_url": "https://example.edu/rsvp/research-writing-workshop",
        "rsvp_deadline": _date(18),
    },
    {
        "external_id": "mock-event-deans-lecture",
        "title": "Dean's Lecture Series: Future of Computing",
        "description": "Prof. Kamau discusses quantum computing and AI trends.",
        "category": "Academic",
        "date": _date(27),
        "start_time": _time(14, 0),
        "end_time": _time(15, 30),
        "location": "LT 1",
        "is_online": False,
        "meeting_url": None,
        "badge": "🎤 Guest Speaker",
        "thumbnail": "https://picsum.photos/seed/deanslecture/600/360",
        "source_url": "https://example.edu/events/deans-lecture-series",
        "source_name": "Faculty of Computing",
        "rsvp_url": None,
        "rsvp_deadline": None,
    },
    {
        "external_id": "mock-event-career-fair",
        "title": "Career Fair 2026",
        "description": "Meet top employers, internships, and graduate opportunities.",
        "category": "Career",
        "date": _date(35),
        "start_time": _time(9, 0),
        "end_time": _time(16, 0),
        "location": "Exhibition Hall",
        "is_online": False,
        "meeting_url": None,
        "badge": "💼 Hiring",
        "thumbnail": "https://picsum.photos/seed/careerfair/600/360",
        "source_url": "https://example.edu/events/career-fair-2026",
        "source_name": "Careers Office",
        "rsvp_url": "https://example.edu/rsvp/career-fair-2026",
        "rsvp_deadline": _date(33),
    },
]


MOCK_NEWS = [
    {
        "external_id": "mock-news-exam-timetable",
        "title": "Semester Exam Timetable Released",
        "summary": "The examination timetable for this semester is now available on the student portal. Check your unit codes carefully for venue and time changes.",
        "category": "Academic",
        "date": _date(-1),
        "source_url": "https://example.edu/news/exam-timetable-released",
        "source_name": "Examinations Office",
        "badge": "📌 Important",
        "thumbnail": "https://picsum.photos/seed/examtimetable/600/360",
    },
    {
        "external_id": "mock-news-fee-deadline",
        "title": "Fee Payment Deadline Extended",
        "summary": "Following requests from student leaders, the fee payment deadline has been pushed back by two weeks. Late penalties will not apply within this window.",
        "category": "Finance",
        "date": _date(-2),
        "source_url": "https://example.edu/news/fee-deadline-extended",
        "source_name": "Finance Office",
        "badge": "⏰ Deadline",
        "thumbnail": "https://picsum.photos/seed/feedeadline/600/360",
    },
    {
        "external_id": "mock-news-library-wing",
        "title": "New Library Wing Opens to Students",
        "summary": "The newly built east wing of the main library is now open, adding over 500 study spaces, group rooms, and an extended digital archive section.",
        "category": "Campus",
        "date": _date(-3),
        "source_url": "https://example.edu/news/library-wing-opens",
        "source_name": "Library Services",
        "badge": None,
        "thumbnail": "https://picsum.photos/seed/librarywing/600/360",
    },
    {
        "external_id": "mock-news-council-results",
        "title": "Student Council Election Results Announced",
        "summary": "Results from this year's student council elections have been ratified by the electoral board. The new executive takes office at the start of next month.",
        "category": "Student Affairs",
        "date": _date(-4),
        "source_url": "https://example.edu/news/council-election-results",
        "source_name": "Student Council",
        "badge": None,
        "thumbnail": "https://picsum.photos/seed/councilresults/600/360",
    },
    {
        "external_id": "mock-news-ranking",
        "title": "University Ranked Top 10 in East Africa",
        "summary": "The university has climbed three places in the latest regional rankings, driven largely by improvements in research output and graduate employability.",
        "category": "Achievement",
        "date": _date(-6),
        "source_url": "https://example.edu/news/top-10-ranking",
        "source_name": "Communications Office",
        "badge": "🏆 Ranking",
        "thumbnail": "https://picsum.photos/seed/ranking/600/360",
    },
    {
        "external_id": "mock-news-wifi-maintenance",
        "title": "Campus WiFi Maintenance Scheduled This Weekend",
        "summary": "IT Services will carry out network upgrades over the weekend. Expect intermittent connectivity in hostels and lecture halls during the maintenance window.",
        "category": "IT",
        "date": _date(-7),
        "source_url": "https://example.edu/news/wifi-maintenance",
        "source_name": "IT Services",
        "badge": "🔧 Maintenance",
        "thumbnail": "https://picsum.photos/seed/wifimaintenance/600/360",
    },
    {
        "external_id": "mock-news-scholarships",
        "title": "Scholarship Applications Now Open",
        "summary": "Applications for need-based and merit scholarships for the next academic year are now open. Submit supporting documents through the financial aid portal.",
        "category": "Opportunities",
        "date": _date(-9),
        "source_url": "https://example.edu/news/scholarship-applications-open",
        "source_name": "Financial Aid Office",
        "badge": "🎓 Apply Now",
        "thumbnail": "https://picsum.photos/seed/scholarships/600/360",
    },
    {
        "external_id": "mock-news-registration-portal",
        "title": "New Course Registration Portal Launched",
        "summary": "A redesigned registration portal is now live, with faster unit selection, real-time clash detection, and mobile support.",
        "category": "Academic",
        "date": _date(-11),
        "source_url": "https://example.edu/news/new-registration-portal",
        "source_name": "ICT Department",
        "badge": "🆕 New",
        "thumbnail": "https://picsum.photos/seed/registrationportal/600/360",
    },
]


class Command(BaseCommand):
    help = "Generate mock EventItem and NewsItem records for testing the socials pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously generated mock records (external_id "
                 "starting with 'mock-event-' / 'mock-news-') before creating new ones.",
        )
        parser.add_argument(
            "--events-only",
            action="store_true",
            help="Only generate EventItem records.",
        )
        parser.add_argument(
            "--news-only",
            action="store_true",
            help="Only generate NewsItem records.",
        )

    def handle(self, *args, **options):
        do_events = not options["news_only"]
        do_news = not options["events_only"]

        if options["clear"]:
            self._clear(do_events, do_news)

        if do_events:
            self._generate_events()

        if do_news:
            self._generate_news()

        self.stdout.write(self.style.SUCCESS("Mock socials data generated."))

    def _clear(self, do_events, do_news):
        if do_events:
            deleted, _ = EventItem.objects.filter(
                external_id__startswith="mock-event-"
            ).delete()
            self.stdout.write(f"Removed {deleted} existing mock event(s).")

        if do_news:
            deleted, _ = NewsItem.objects.filter(
                external_id__startswith="mock-news-"
            ).delete()
            self.stdout.write(f"Removed {deleted} existing mock news item(s).")

    def _generate_events(self):
        created, updated = 0, 0

        for data in MOCK_EVENTS:
            defaults = {k: v for k, v in data.items() if k != "external_id"}
            defaults["is_published"] = True

            _, was_created = EventItem.objects.update_or_create(
                external_id=data["external_id"],
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Events: {created} created, {updated} updated.")
        )

    def _generate_news(self):
        created, updated = 0, 0

        for data in MOCK_NEWS:
            defaults = {k: v for k, v in data.items() if k != "external_id"}
            defaults["is_published"] = True

            _, was_created = NewsItem.objects.update_or_create(
                external_id=data["external_id"],
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"News: {created} created, {updated} updated.")
        )
