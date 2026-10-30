"""Explicit response projections; internal keys and user emails stay private."""
def record(item, **fields):
    return {'id': str(item.id), 'created_at': item.created_at.isoformat(), **fields}


def organization(item):
    return record(item, name=item.name)


def project(item):
    return record(item, organization_id=str(item.organization_id), title=item.title, currency=item.currency)


def revision(item):
    return record(item, scenario_id=str(item.scenario_id), number=item.number, inputs=item.inputs, context=item.context)


def scenario(item, detail=False):
    result = record(item, project_id=str(item.project_id), title=item.title)
    if detail:
        # History is separately paginated; creation/detail carries just the latest revision.
        latest = item.revisions.order_by('-number').first()
        result = {**result, 'revisions': [revision(latest)] if latest else []}
    return result


def run(item):
    return record(item, revision_id=str(item.revision_id), project_id=str(item.revision.scenario.project_id), status=item.status,
                  inputs=item.inputs, context=item.context, results=item.results, engine_version=item.engine_version,
                  assumptions=item.assumptions)


def member(item):
    return record(item, username=item.user.username, role=item.role, active=item.active)
