from django.urls import path

from . import views

urlpatterns = [
    path("", views.root, name="root"),
    path("users/", views.list_users, name="user-list"),
    path("users/<int:user_id>/", views.get_user, name="user-detail"),
    path("users/", views.create_user, name="user-create"),
    path("users/<int:user_id>/", views.delete_user, name="user-delete"),
]
