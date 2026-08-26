from django.contrib import admin

from .models import Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "short_user_agent", "visited_at")
    search_fields = ("ip_address", "user_agent")
    ordering = ("-visited_at",)
    list_filter = ("visited_at",)
    date_hierarchy = "visited_at"

    @admin.display(description="User Agent")
    def short_user_agent(self, obj: Visitor) -> str:
        return obj.user_agent[:80] + ("..." if len(obj.user_agent) > 80 else "")
