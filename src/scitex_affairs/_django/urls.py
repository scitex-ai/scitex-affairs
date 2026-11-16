"""Mount-safe routes for the business browser app."""

from django.urls import path

from . import views

app_name = "scitex_affairs"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/report", views.report_api, name="report_api"),
]
