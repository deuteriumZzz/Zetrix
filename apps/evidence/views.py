from django.shortcuts import get_object_or_404
from apps.workspaces.api import WorkspaceAPIView, ok, page
from . import presentation as present, serializers as schema, services
from .models import Event, EvidenceSource


def visible_events(user, history=False):
    events = Event.objects.select_related('published_revision').order_by('-created_at', '-id')
    if user.is_staff:
        return events
    if history:
        return events.filter(publications__action='publish').distinct()
    return events.filter(published_revision__isnull=False)


class SourcesView(WorkspaceAPIView):
    def get(self, request):
        # Registry is intentionally shared metadata; draft event contents remain private.
        return page(EvidenceSource.objects.all(), request, present.source)

    def post(self, request):
        services.require_curator(request.user)
        data = schema.validated(schema.SourceInput, request.data)
        return ok(present.source(services.create_source(request.user, data)), status=201)


class EventsView(WorkspaceAPIView):
    def get(self, request):
        return page(visible_events(request.user, history=True), request,
                    lambda item: present.event(item, request.user.is_staff))

    def post(self, request):
        services.require_curator(request.user)
        data = schema.validated(schema.RevisionInput, request.data)
        return ok(present.event(services.create_event(request.user, data), True), status=201)


class EventView(WorkspaceAPIView):
    def get(self, request, event_id):
        item = get_object_or_404(visible_events(request.user, history=True), id=event_id)
        return ok(present.event(item, request.user.is_staff))


class RevisionsView(WorkspaceAPIView):
    def get(self, request, event_id):
        item = get_object_or_404(visible_events(request.user, history=True), id=event_id)
        revisions = item.revisions.select_related('event').order_by('-number')
        if not request.user.is_staff:
            revisions = revisions.filter(publications__action='publish').distinct()
        return page(revisions, request, present.revision)

    def post(self, request, event_id):
        services.require_curator(request.user)
        data = schema.validated(schema.RevisionInput, request.data)
        return ok(present.revision(services.create_revision(event_id, request.user, data)), status=201)


class PublishView(WorkspaceAPIView):
    def post(self, request, event_id):
        services.require_curator(request.user)
        data = schema.validated(schema.PublishInput, request.data)
        return ok(present.event(services.publish(event_id, data['revision_id'], request.user), True))


class RevokeView(WorkspaceAPIView):
    def post(self, request, event_id):
        services.require_curator(request.user)
        data = schema.validated(schema.RevokeInput, request.data)
        return ok(present.event(services.revoke(event_id, request.user, data['reason']), True))
