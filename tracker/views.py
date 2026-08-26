from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, ProgrammingError, transaction
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from .ip_utils import get_client_ip
from .models import Visitor


def visitor_storage_available() -> bool:
    try:
        Visitor.objects.exists()
        return True
    except (OperationalError, ProgrammingError):
        return False


def auth_storage_available() -> bool:
    try:
        get_user_model().objects.exists()
        return True
    except (OperationalError, ProgrammingError):
        return False


def should_ignore_user_agent(user_agent: str) -> bool:
    ignored_keywords = getattr(settings, "IGNORED_USER_AGENT_KEYWORDS", [])
    lowered_user_agent = user_agent.lower()
    return any(keyword.lower() in lowered_user_agent for keyword in ignored_keywords)


def log_latest_visit(request) -> None:
    ip_address = get_client_ip(request)
    connection_ip = (request.META.get("REMOTE_ADDR") or "").strip() or None
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:1000]
    if should_ignore_user_agent(user_agent):
        return

    with transaction.atomic():
        visitor, created = Visitor.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                "connection_ip": connection_ip,
                "user_agent": user_agent,
            },
        )
        if not created:
            visitor.connection_ip = connection_ip
            visitor.visited_at = timezone.now()
            visitor.save(update_fields=["connection_ip", "user_agent", "visited_at"])


def index(request):
    if visitor_storage_available():
        log_latest_visit(request)
    return render(request, "tracker/index.html")


def iplogs(request):
    auth_ready = auth_storage_available()
    if not auth_ready:
        context = {
            "page_obj": Paginator(Visitor.objects.none(), 20).get_page(request.GET.get("page")),
            "search_query": request.GET.get("q", "").strip(),
            "stats": {
                "total_visits": 0,
                "unique_ips": 0,
                "todays_visits": 0,
            },
            "database_ready": False,
            "auth_ready": False,
        }
        return render(request, "tracker/iplogs.html", context, status=200)

    if not request.user.is_authenticated:
        return HttpResponseRedirect(f"/admin/login/?next={request.path}")

    if not request.user.is_staff:
        raise PermissionDenied("Staff access is required.")

    search_query = request.GET.get("q", "").strip()
    database_ready = visitor_storage_available()

    if database_ready:
        visitor_qs = Visitor.objects.all()
        if search_query:
            visitor_qs = visitor_qs.filter(ip_address__icontains=search_query)

        paginator = Paginator(visitor_qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        today = timezone.localdate()
        stats = {
            "total_visits": Visitor.objects.count(),
            "unique_ips": Visitor.objects.aggregate(total=Count("ip_address", distinct=True))["total"] or 0,
            "todays_visits": Visitor.objects.filter(visited_at__date=today).count(),
        }
    else:
        paginator = Paginator(Visitor.objects.none(), 20)
        page_obj = paginator.get_page(request.GET.get("page"))
        stats = {
            "total_visits": 0,
            "unique_ips": 0,
            "todays_visits": 0,
        }

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "stats": stats,
        "database_ready": database_ready,
        "auth_ready": True,
    }
    return render(request, "tracker/iplogs.html", context)


def iplogs_alias_redirect(request):
    return HttpResponseRedirect("/iplogs/")
