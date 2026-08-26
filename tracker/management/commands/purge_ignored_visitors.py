from django.conf import settings
from django.core.management.base import BaseCommand

from tracker.models import Visitor


class Command(BaseCommand):
    help = "Delete visitor rows with ignored user-agent keywords."

    def handle(self, *args, **options):
        ignored_keywords = getattr(settings, "IGNORED_USER_AGENT_KEYWORDS", [])
        deleted_total = 0

        for keyword in ignored_keywords:
            deleted_count, _ = Visitor.objects.filter(user_agent__icontains=keyword).delete()
            deleted_total += deleted_count

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_total} ignored visitor row(s)."))
