from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .ip_utils import get_client_ip
from .models import Visitor


def index(request):
    Visitor.objects.create(
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
    )
    return render(request, "tracker/index.html")


@login_required(login_url="/admin/login/")
def iplogs(request):
    if not request.user.is_staff:
        raise PermissionDenied("Staff access is required.")

    search_query = request.GET.get("q", "").strip()
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

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "stats": stats,
    }
    return render(request, "tracker/iplogs.html", context)
