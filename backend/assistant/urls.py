from django.urls import path

from . import views

urlpatterns = [
    path("groups/<int:group_id>/assistant", views.Assistant.as_view()),
    path("assistant/scan", views.Scan.as_view()),
    path("groups/<int:group_id>/assistant/transcribe", views.Transcribe.as_view()),
]
