from .services import revision_snapshot, source_snapshot


def source(item):
    return {**source_snapshot(item), 'created_at': item.created_at.isoformat()}


def revision(item):
    return {**revision_snapshot(item), 'id': str(item.id), 'number': item.number,
            'created_at': item.created_at.isoformat()}


def event(item, staff=False):
    result = {'id': str(item.id), 'created_at': item.created_at.isoformat(),
              'published_revision': revision(item.published_revision) if item.published_revision_id else None}
    if not item.published_revision_id:
        previous = item.publications.filter(action='publish').select_related('revision').order_by('-created_at', '-id').first()
        result = {**result, 'historical_revision': revision(previous.revision) if previous else None}
    if staff:
        latest = item.revisions.order_by('-number').first()
        result = {**result, 'latest_revision': revision(latest) if latest else None}
    return result
