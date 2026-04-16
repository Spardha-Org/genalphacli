from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"posts", views.PostViewSet, basename="post")

urlpatterns = [
    path("", include(router.urls)),
    path("stats/", views.StatsView.as_view(), name="stats"),
]
