from django.urls import path, include

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("api/v1/", include("api.urls")),
]
