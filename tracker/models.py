from django.db import models


class Visitor(models.Model):
    ip_address = models.GenericIPAddressField(db_index=True, unique=True)
    user_agent = models.TextField(blank=True)
    visited_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-visited_at"]

    def __str__(self) -> str:
        return f"{self.ip_address} @ {self.visited_at:%Y-%m-%d %H:%M:%S}"
