"""Session-only scenario workspace API. All records are scoped through membership."""
import re

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.permissions import AllowAny

from . import presentation as present
from . import serializers as schema
from . import services
from .api import LoginThrottle, WorkspaceAPIView, ok, page
from .models import Membership, Organization, ScenarioRun


class CsrfView(WorkspaceAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return ok({'csrf_token': get_token(request._request)})


class LoginView(WorkspaceAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        # SessionAuthentication skips CSRF for anonymous requests; login must not.
        SessionAuthentication().enforce_csrf(request)
        data = schema.validated(schema.LoginInput, request.data)
        user = authenticate(request=request._request, **data)
        if user is None:
            raise AuthenticationFailed('Invalid username or password.')
        login(request._request, user)
        return ok({'id': user.pk, 'username': user.username, 'is_staff': user.is_staff, 'csrf_token': get_token(request._request)})


class LogoutView(WorkspaceAPIView):
    def post(self, request):
        logout(request._request)
        return ok()


class MeView(WorkspaceAPIView):
    def get(self, request):
        return ok({'id': request.user.pk, 'username': request.user.username, 'is_staff': request.user.is_staff})


class OrganizationsView(WorkspaceAPIView):
    def get(self, request):
        items = Organization.objects.filter(memberships__user=request.user, memberships__active=True)
        return page(items, request, present.organization)

    def post(self, request):
        data = schema.validated(schema.OrganizationInput, request.data)
        return ok(present.organization(services.create_organization(request.user, data)), status=201)


class OrganizationView(WorkspaceAPIView):
    def get(self, request, org_id):
        org, member = services.membership(org_id, request.user)
        return ok({**present.organization(org), 'role': member.role})


class ProjectsView(WorkspaceAPIView):
    def get(self, request, org_id):
        org, _ = services.membership(org_id, request.user)
        return page(org.projects.all(), request, present.project)

    def post(self, request, org_id):
        data = schema.validated(schema.ProjectInput, request.data)
        return ok(present.project(services.create_project(org_id, request.user, data)), status=201)


class ProjectView(WorkspaceAPIView):
    def get(self, request, org_id, project_id):
        org, _ = services.membership(org_id, request.user)
        return ok(present.project(services.scoped_project(org, project_id)))


class ScenariosView(WorkspaceAPIView):
    def get(self, request, org_id, project_id):
        org, _ = services.membership(org_id, request.user)
        project = services.scoped_project(org, project_id)
        return page(project.scenarios.all(), request, present.scenario)

    def post(self, request, org_id, project_id):
        data = schema.validated(schema.ScenarioInput, request.data)
        item = services.create_scenario(org_id, project_id, request.user, data)
        return ok(present.scenario(item, detail=True), status=201)


class ScenarioView(WorkspaceAPIView):
    def get(self, request, org_id, project_id, scenario_id):
        org, _ = services.membership(org_id, request.user)
        item = services.scoped_scenario(org, project_id, scenario_id)
        return ok(present.scenario(item, detail=True))


class RevisionsView(WorkspaceAPIView):
    def get(self, request, org_id, project_id, scenario_id):
        org, _ = services.membership(org_id, request.user)
        item = services.scoped_scenario(org, project_id, scenario_id)
        return page(item.revisions.order_by('-number'), request, present.revision)

    def post(self, request, org_id, project_id, scenario_id):
        data = schema.validated(schema.RevisionInput, request.data)
        item = services.create_revision(org_id, project_id, scenario_id, request.user, data)
        return ok(present.revision(item), status=201)


class RunsView(WorkspaceAPIView):
    def get(self, request, org_id):
        org, _ = services.membership(org_id, request.user)
        return page(org.runs.order_by('-created_at', '-id'), request, present.run)

    def post(self, request, org_id):
        data = schema.validated(schema.RunInput, request.data)
        key = request.headers.get('Idempotency-Key', '')
        if not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', key):
            raise ValidationError({'Idempotency-Key': 'Provide 1–128 ASCII letters, digits, . _ : or -.'})
        item, created = services.create_run(org_id, request.user, data['revision_id'], key)
        return ok(present.run(item), status=201 if created else 200)


class RunView(WorkspaceAPIView):
    def get(self, request, org_id, run_id):
        org, _ = services.membership(org_id, request.user)
        item = get_object_or_404(ScenarioRun, organization=org, id=run_id)
        return ok(present.run(item))


class RunExportView(WorkspaceAPIView):
    def get(self, request, org_id, run_id):
        item = services.export_run(org_id, run_id, request.user)
        response = ok(present.run(item))
        response['Content-Disposition'] = f'attachment; filename="zetrix-run-{run_id}.json"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class MembersView(WorkspaceAPIView):
    def get(self, request, org_id):
        org, _ = services.membership(org_id, request.user)
        return page(Membership.objects.filter(organization=org).select_related('user'), request, present.member)

    def post(self, request, org_id):
        data = schema.validated(schema.MemberInput, request.data)
        return ok(present.member(services.add_member(org_id, request.user, data)), status=201)


class MemberView(WorkspaceAPIView):
    def patch(self, request, org_id, member_id):
        data = schema.validated(schema.MemberUpdate, request.data)
        return ok(present.member(services.update_member(org_id, member_id, request.user, data)))


class UnknownRouteView(WorkspaceAPIView):
    permission_classes = [AllowAny]

    def get(self, request, unmatched=''):
        raise NotFound('API resource not found.')

    post = put = patch = delete = options = head = get
