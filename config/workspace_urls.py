"""Isolated v2 URL configuration shared by MVP deployment and tests."""
from django.urls import include, path

urlpatterns = [
    path('api/v2/evidence/', include('apps.evidence.urls')),
    path('api/v2/', include('apps.decisions.urls')),
    path('api/v2/', include('apps.workspaces.urls')),
]
