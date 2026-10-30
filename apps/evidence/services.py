"""Staff-curated evidence with immutable history and an explicit approval pointer."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Event, EventRevision, EvidenceSource, Publication


def require_curator(user):
    if not user.is_active or not user.is_staff:
        raise PermissionDenied('Only platform curators may manage evidence.')


def source_snapshot(source):
    return {'id': str(source.id), 'publisher': source.publisher, 'url': source.url,
            'allowed_use': source.allowed_use}


def create_source(user, data):
    require_curator(user)
    return EvidenceSource.objects.create(created_by=user, **data)


def revision_values(data):
    sources = {item.id: item for item in EvidenceSource.objects.filter(id__in=data['source_ids'])}
    if len(sources) != len(data['source_ids']):
        raise ValidationError({'source_ids': 'One or more sources do not exist.'})
    return {**{key: value for key, value in data.items() if key != 'source_ids'},
            'sources': [source_snapshot(sources[source_id]) for source_id in data['source_ids']]}


@transaction.atomic
def create_event(user, data):
    require_curator(user)
    values = revision_values(data)
    event = Event.objects.create(created_by=user)
    EventRevision.objects.create(event=event, number=1, created_by=user, **values)
    return event


@transaction.atomic
def create_revision(event_id, user, data):
    require_curator(user)
    event = get_object_or_404(Event.objects.select_for_update(), id=event_id)
    latest = event.revisions.order_by('-number').first()
    return EventRevision.objects.create(event=event, number=latest.number + 1, created_by=user,
                                        **revision_values(data))


@transaction.atomic
def publish(event_id, revision_id, user):
    require_curator(user)
    event = get_object_or_404(Event.objects.select_for_update(), id=event_id)
    revision = get_object_or_404(EventRevision, event=event, id=revision_id)
    if event.published_revision_id != revision.id:
        Publication.objects.create(event=event, revision=revision, action='publish', actor=user)
        Event.objects.filter(id=event.id).update(published_revision=revision)
    return Event.objects.get(id=event.id)


@transaction.atomic
def revoke(event_id, user, reason):
    require_curator(user)
    event = get_object_or_404(Event.objects.select_for_update(), id=event_id)
    if not event.published_revision_id:
        raise ValidationError('This event has no current publication.')
    Publication.objects.create(event=event, revision_id=event.published_revision_id,
                               action='revoke', reason=reason, actor=user)
    Event.objects.filter(id=event.id).update(published_revision=None)
    return Event.objects.get(id=event.id)


def publication_status(revision):
    if revision.event.published_revision_id == revision.id:
        return 'current'
    last = revision.publications.order_by('-created_at', '-id').first()
    if last is None:
        return 'draft'
    return 'withdrawn' if last.action == 'revoke' else 'superseded'


def revision_snapshot(revision):
    return {'event_id': str(revision.event_id), 'revision_id': str(revision.id),
            'revision_number': revision.number, 'title': revision.title, 'summary': revision.summary,
            'event_kind': revision.event_kind, 'country_codes': list(revision.country_codes),
            'effective_at': revision.effective_at.isoformat(), 'provenance': revision.provenance,
            'sources': [dict(source) for source in revision.sources],
            'publication_status': publication_status(revision)}


@transaction.atomic
def get_published_snapshot(revision_id):
    """Only current approvals can be attached to new scenario revisions.

    The parent event lock remains held until an enclosing scenario transaction commits.
    Stored scenario snapshots survive later publication changes without being rewritten.
    """
    revision = EventRevision.objects.filter(id=revision_id).first()
    if revision is None:
        raise ValidationError({'evidence_revision_id': 'Select a current approved evidence revision.'})
    event = Event.objects.select_for_update().get(id=revision.event_id)
    if event.published_revision_id != revision.id:
        raise ValidationError({'evidence_revision_id': 'Select a current approved evidence revision.'})
    return {**revision_snapshot(revision), 'publication_status': 'current'}
