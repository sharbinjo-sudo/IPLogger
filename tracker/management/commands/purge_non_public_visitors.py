from django.core.management.base import BaseCommand

from tracker.ip_utils import is_public_ip
from tracker.models import Visitor


class Command(BaseCommand):
    help = "Delete visitor rows whose public IP field is not actually public."

    def handle(self, *args, **options):
        deleted_total = 0

        for visitor in Visitor.objects.only("id", "ip_address"):
            if not is_public_ip(visitor.ip_address):
                visitor.delete()
                deleted_total += 1

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_total} non-public visitor row(s)."))
