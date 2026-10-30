from django.urls import path
from .views import DecisionsView, DecisionView, RunCSVView

app_name = 'decisions'
org = 'organizations/<uuid:org_id>/'
urlpatterns = [
    path(org + 'decisions/', DecisionsView.as_view(), name='decisions'),
    path(org + 'decisions/<uuid:decision_id>/', DecisionView.as_view(), name='decision'),
    path(org + 'runs/<uuid:run_id>/csv/', RunCSVView.as_view(), name='run-csv'),
]
