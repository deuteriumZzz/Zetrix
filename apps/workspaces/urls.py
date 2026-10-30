from django.urls import path
from . import views, portfolio_views

app_name = 'workspaces'
org = 'organizations/<uuid:org_id>/'
project = org + 'projects/<uuid:project_id>/'
scenario = project + 'scenarios/<uuid:scenario_id>/'
urlpatterns = [
    path('auth/csrf/', views.CsrfView.as_view(), name='csrf'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/me/', views.MeView.as_view(), name='me'),
    path('organizations/', views.OrganizationsView.as_view(), name='organizations'),
    path(org, views.OrganizationView.as_view(), name='organization'),
    path(org + 'projects/', views.ProjectsView.as_view(), name='projects'),
    path(project + 'portfolio/', portfolio_views.PortfoliosView.as_view(), name='portfolio'),
    path(project + 'portfolio/preview/', portfolio_views.PortfolioPreviewView.as_view(), name='portfolio-preview'),
    path(project + 'portfolio/imports/<uuid:import_id>/confirm/', portfolio_views.PortfolioConfirmView.as_view(), name='portfolio-confirm'),
    path(project, views.ProjectView.as_view(), name='project'),
    path(project + 'scenarios/', views.ScenariosView.as_view(), name='scenarios'),
    path(scenario, views.ScenarioView.as_view(), name='scenario'),
    path(scenario + 'revisions/', views.RevisionsView.as_view(), name='revisions'),
    path(org + 'runs/', views.RunsView.as_view(), name='runs'),
    path(org + 'runs/<uuid:run_id>/', views.RunView.as_view(), name='run'),
    path(org + 'runs/<uuid:run_id>/export/', views.RunExportView.as_view(), name='run-export'),
    path(org + 'members/', views.MembersView.as_view(), name='members'),
    path(org + 'members/<uuid:member_id>/', views.MemberView.as_view(), name='member'),
    path('', views.UnknownRouteView.as_view()),
    path('<path:unmatched>', views.UnknownRouteView.as_view()),
]
