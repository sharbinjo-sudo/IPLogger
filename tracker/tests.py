from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse

from . import views
from .models import Visitor


User = get_user_model()


class TrackerViewTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="safe-password-123",
            is_staff=True,
        )
        self.non_staff_user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="safe-password-123",
            is_staff=False,
        )

    def test_homepage_returns_http_200(self) -> None:
        request = self.factory.get(reverse("tracker:index"), REMOTE_ADDR="127.0.0.1")
        response = views.index(request)
        self.assertEqual(response.status_code, 200)

    def test_homepage_creates_visitor_record(self) -> None:
        request = self.factory.get(reverse("tracker:index"), REMOTE_ADDR="127.0.0.1")
        views.index(request)
        self.assertEqual(Visitor.objects.count(), 1)

    def test_correct_ip_is_stored_for_local_request(self) -> None:
        request = self.factory.get(reverse("tracker:index"), REMOTE_ADDR="127.0.0.42")
        views.index(request)
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.ip_address, "127.0.0.42")
        self.assertEqual(visitor.connection_ip, "127.0.0.42")

    def test_ignored_uptime_robot_user_agent_is_not_recorded(self) -> None:
        request = self.factory.get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.88",
            HTTP_USER_AGENT="Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)",
        )
        response = views.index(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Visitor.objects.count(), 0)

    def test_repeated_ip_updates_existing_visitor_record(self) -> None:
        first_request = self.factory.get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.55",
            HTTP_USER_AGENT="First browser",
        )
        second_request = self.factory.get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.55",
            HTTP_USER_AGENT="Latest browser",
        )

        views.index(first_request)
        first_visited_at = Visitor.objects.get().visited_at
        views.index(second_request)
        visitor = Visitor.objects.get()

        self.assertEqual(Visitor.objects.count(), 1)
        self.assertEqual(visitor.connection_ip, "127.0.0.55")
        self.assertEqual(visitor.user_agent, "Latest browser")
        self.assertGreaterEqual(visitor.visited_at, first_visited_at)

    def test_anonymous_users_cannot_access_iplogs(self) -> None:
        response = self.client.get(reverse("tracker:iplogs"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_staff_authenticated_users_cannot_access_iplogs(self) -> None:
        self.client.force_login(self.non_staff_user)
        response = self.client.get(reverse("tracker:iplogs"))
        self.assertEqual(response.status_code, 403)

    def test_staff_users_can_access_iplogs(self) -> None:
        request = self.factory.get(reverse("tracker:iplogs"))
        request.user = self.staff_user
        response = views.iplogs(request)
        self.assertEqual(response.status_code, 200)

    def test_pagination_works(self) -> None:
        for index in range(1, 26):
            Visitor.objects.create(ip_address=f"10.0.0.{index}", user_agent="Mozilla/5.0")

        request = self.factory.get(reverse("tracker:iplogs"), {"page": 2})
        request.user = self.staff_user
        with patch("tracker.views.render", return_value=HttpResponse("ok")) as mock_render:
            response = views.iplogs(request)

        self.assertEqual(response.status_code, 200)
        context = mock_render.call_args.args[2]
        self.assertEqual(len(context["page_obj"].object_list), 5)

    def test_dashboard_statistics_are_correct(self) -> None:
        Visitor.objects.create(ip_address="10.0.0.1", user_agent="UA 1")
        Visitor.objects.create(ip_address="10.0.0.3", user_agent="UA 2")
        Visitor.objects.create(ip_address="10.0.0.2", user_agent="UA 3")
        request = self.factory.get(reverse("tracker:iplogs"))
        request.user = self.staff_user
        with patch("tracker.views.render", return_value=HttpResponse("ok")) as mock_render:
            views.iplogs(request)

        context = mock_render.call_args.args[2]
        self.assertEqual(context["stats"]["total_visits"], 3)
        self.assertEqual(context["stats"]["unique_ips"], 3)
        self.assertEqual(context["stats"]["todays_visits"], 3)

    def test_search_by_ip_works(self) -> None:
        Visitor.objects.create(ip_address="10.0.0.1", user_agent="Match")
        Visitor.objects.create(ip_address="192.168.0.1", user_agent="Miss")
        request = self.factory.get(reverse("tracker:iplogs"), {"q": "10.0.0"})
        request.user = self.staff_user
        with patch("tracker.views.render", return_value=HttpResponse("ok")) as mock_render:
            response = views.iplogs(request)

        self.assertEqual(response.status_code, 200)
        context = mock_render.call_args.args[2]
        self.assertEqual(list(context["page_obj"].object_list.values_list("ip_address", flat=True)), ["10.0.0.1"])


class ProxyIpTests(TestCase):
    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_trusted_proxy_uses_forwarded_for(self) -> None:
        request = RequestFactory().get(
            reverse("tracker:index"),
            REMOTE_ADDR="10.10.10.10",
            HTTP_X_FORWARDED_FOR="8.8.4.4",
        )
        response = views.index(request)
        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.ip_address, "8.8.4.4")
        self.assertEqual(visitor.connection_ip, "10.10.10.10")

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_trusted_proxy_prefers_first_public_forwarded_ip(self) -> None:
        request = RequestFactory().get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.1",
            HTTP_X_FORWARDED_FOR="9.9.9.9, 10.0.0.10, 127.0.0.1",
        )
        response = views.index(request)

        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.ip_address, "9.9.9.9")

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_trusted_proxy_uses_cloudflare_connecting_ip(self) -> None:
        request = RequestFactory().get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.1",
            HTTP_CF_CONNECTING_IP="8.8.8.8",
            HTTP_X_FORWARDED_FOR="1.1.1.1",
        )
        response = views.index(request)

        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.ip_address, "8.8.8.8")

    @override_settings(TRUSTED_PROXY_HOPS=0)
    def test_local_development_uses_remote_addr(self) -> None:
        request = RequestFactory().get(
            reverse("tracker:index"),
            REMOTE_ADDR="127.0.0.1",
            HTTP_X_FORWARDED_FOR="8.8.8.8",
        )
        response = views.index(request)

        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.ip_address, "127.0.0.1")


class MissingTableFallbackTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username="fallback-staff@example.com",
            email="fallback-staff@example.com",
            password="safe-password-123",
            is_staff=True,
        )

    def test_homepage_still_renders_when_visitor_table_is_unavailable(self) -> None:
        request = self.factory.get(reverse("tracker:index"), REMOTE_ADDR="127.0.0.1")
        with patch("tracker.views.visitor_storage_available", return_value=False):
            response = views.index(request)

        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_empty_state_when_visitor_table_is_unavailable(self) -> None:
        request = self.factory.get(reverse("tracker:iplogs"))
        request.user = self.staff_user

        with patch("tracker.views.visitor_storage_available", return_value=False):
            with patch("tracker.views.render", return_value=HttpResponse("ok")) as mock_render:
                response = views.iplogs(request)

        self.assertEqual(response.status_code, 200)
        context = mock_render.call_args.args[2]
        self.assertFalse(context["database_ready"])
        self.assertEqual(context["stats"]["total_visits"], 0)
        self.assertEqual(len(context["page_obj"].object_list), 0)

    def test_dashboard_renders_fallback_when_auth_table_is_unavailable(self) -> None:
        request = self.factory.get(reverse("tracker:iplogs"))
        request.user = self.staff_user

        with patch("tracker.views.auth_storage_available", return_value=False):
            with patch("tracker.views.render", return_value=HttpResponse("ok")) as mock_render:
                response = views.iplogs(request)

        self.assertEqual(response.status_code, 200)
        context = mock_render.call_args.args[2]
        self.assertFalse(context["auth_ready"])
        self.assertEqual(context["stats"]["total_visits"], 0)

    def test_iplogs_alias_redirects_to_canonical_url(self) -> None:
        response = self.client.get("/iplogd")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/iplogs/")
