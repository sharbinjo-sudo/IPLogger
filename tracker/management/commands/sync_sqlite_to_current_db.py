from __future__ import annotations

import sqlite3
from datetime import timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tracker.models import Visitor


class Command(BaseCommand):
    help = "Copy local SQLite users and visitor logs into the currently configured database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite-path",
            default=str(settings.BASE_DIR / "db.sqlite3"),
            help="Path to the source SQLite database.",
        )

    def handle(self, *args, **options):
        sqlite_path = Path(options["sqlite_path"])
        if not sqlite_path.exists():
            raise CommandError(f"SQLite database not found: {sqlite_path}")

        if connection.vendor == "sqlite":
            raise CommandError("The target database is SQLite. Set DATABASE_URL to Neon before syncing.")

        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        try:
            user_count = self.sync_users(sqlite_conn)
            visitor_count = self.sync_visitors(sqlite_conn)
        finally:
            sqlite_conn.close()

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {user_count} user(s) and {visitor_count} visitor log row(s)."
            )
        )

    def sync_users(self, sqlite_conn) -> int:
        User = get_user_model()
        rows = sqlite_conn.execute(
            """
            SELECT username, password, email, first_name, last_name, is_staff,
                   is_active, is_superuser, last_login, date_joined
            FROM auth_user
            """
        ).fetchall()

        synced = 0
        for row in rows:
            last_login = self.parse_sqlite_datetime(row["last_login"]) if row["last_login"] else None
            date_joined = self.parse_sqlite_datetime(row["date_joined"]) if row["date_joined"] else None
            defaults = {
                "email": row["email"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "is_staff": bool(row["is_staff"]),
                "is_active": bool(row["is_active"]),
                "is_superuser": bool(row["is_superuser"]),
                "last_login": last_login,
                "date_joined": date_joined,
            }

            with transaction.atomic():
                user, created = User.objects.update_or_create(
                    username=row["username"],
                    defaults=defaults,
                )
                user.password = row["password"]
                user.save(update_fields=["password"])

            synced += 1
        return synced

    def sync_visitors(self, sqlite_conn) -> int:
        rows = sqlite_conn.execute(
            "SELECT ip_address, user_agent, visited_at FROM tracker_visitor ORDER BY id"
        ).fetchall()

        synced = 0
        for row in rows:
            visited_at = self.parse_sqlite_datetime(row["visited_at"])
            visitor, _ = Visitor.objects.update_or_create(
                ip_address=row["ip_address"],
                defaults={
                    "user_agent": row["user_agent"],
                },
            )
            Visitor.objects.filter(pk=visitor.pk).update(visited_at=visited_at)
            synced += 1
        return synced

    def parse_sqlite_datetime(self, value: str):
        parsed = parse_datetime(value)
        if parsed and timezone.is_naive(parsed):
            return timezone.make_aware(parsed, datetime_timezone.utc)
        return parsed
