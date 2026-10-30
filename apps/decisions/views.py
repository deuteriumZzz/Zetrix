import re
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from apps.workspaces.api import WorkspaceAPIView, ok, page
from apps.workspaces.serializers import validated
from apps.workspaces.services import membership
from .models import Decision
from .serializers import DecisionInput, projected
from .services import create_decision, export_csv


class DecisionsView(WorkspaceAPIView):
    def get(self, request, org_id):
        org, _ = membership(org_id, request.user)
        return page(Decision.objects.filter(organization=org).order_by('-created_at', '-id'), request, projected)

    def post(self, request, org_id):
        data = validated(DecisionInput, request.data)
        key = request.headers.get('Idempotency-Key', '')
        if not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', key):
            raise ValidationError({'Idempotency-Key': 'Provide 1–128 ASCII letters, digits, . _ : or -.'})
        item, created = create_decision(org_id, request.user, data, key)
        return ok(projected(item), status=201 if created else 200)


class DecisionView(WorkspaceAPIView):
    def get(self, request, org_id, decision_id):
        org, _ = membership(org_id, request.user)
        return ok(projected(get_object_or_404(Decision, organization=org, id=decision_id)))


class RunCSVView(WorkspaceAPIView):
    def get(self, request, org_id, run_id):
        content = export_csv(org_id, run_id, request.user)
        response = HttpResponse('\ufeff' + content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="zetrix-run-{run_id}.csv"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        if hasattr(response, 'data'):
            return super().finalize_response(request, response, *args, **kwargs)
        response = APIView.finalize_response(self, request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['X-Request-ID'] = self.request_id
        return response
