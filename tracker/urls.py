from django.urls import path

from . import views


app_name = "tracker"

urlpatterns = [
    path("", views.index, name="index"),
    path("iplog/", views.iplogs_alias_redirect, name="iplogs-alias-iplog"),
    path("iplogd", views.iplogs_alias_redirect, name="iplogs-alias-iplogd"),
    path("iplogger", views.iplogs_alias_redirect, name="iplogs-alias-iplogger"),
    path("iplogs/", views.iplogs, name="iplogs"),
]
