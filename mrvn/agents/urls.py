"""URL configuration for the agents app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from agents.views import AgentViewSet, ToolViewSet

router = DefaultRouter()
router.register(r"agents", AgentViewSet, basename="agent")
router.register(r"tools", ToolViewSet, basename="tool")

urlpatterns = [
    path("", include(router.urls)),
]
