"""Project-scoped portfolio API; staged CSV data is never a filesystem upload."""
from . import portfolio, services
from .api import WorkspaceAPIView, ok, page
from .portfolio_serializers import CSVPreviewInput, ConfirmInput, PortfolioInput
from .serializers import validated


class PortfoliosView(WorkspaceAPIView):
    def get(self, request, org_id, project_id):
        org, _ = services.membership(org_id, request.user)
        project = services.scoped_project(org, project_id)
        return page(project.portfolio_revisions.order_by('-number'), request, portfolio.projected)

    def post(self, request, org_id, project_id):
        data = validated(PortfolioInput, request.data)
        item = portfolio.create_manual(org_id, project_id, request.user, data['lines'])
        return ok(portfolio.projected(item), status=201)


class PortfolioPreviewView(WorkspaceAPIView):
    def post(self, request, org_id, project_id):
        data = validated(CSVPreviewInput, request.data)
        item = portfolio.preview_csv(org_id, project_id, request.user, data['csv'])
        return ok(portfolio.projected(item), status=201)


class PortfolioConfirmView(WorkspaceAPIView):
    def post(self, request, org_id, project_id, import_id):
        validated(ConfirmInput, request.data)
        item, created = portfolio.confirm_import(org_id, project_id, import_id, request.user)
        return ok(portfolio.projected(item), status=201 if created else 200)
