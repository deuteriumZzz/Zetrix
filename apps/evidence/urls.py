from django.urls import path
from . import views

app_name = 'evidence'
urlpatterns = [
    path('sources/', views.SourcesView.as_view(), name='sources'),
    path('events/', views.EventsView.as_view(), name='events'),
    path('events/<uuid:event_id>/', views.EventView.as_view(), name='event'),
    path('events/<uuid:event_id>/revisions/', views.RevisionsView.as_view(), name='revisions'),
    path('events/<uuid:event_id>/publish/', views.PublishView.as_view(), name='publish'),
    path('events/<uuid:event_id>/revoke/', views.RevokeView.as_view(), name='revoke'),
]
