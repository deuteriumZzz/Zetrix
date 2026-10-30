"""Immutable portfolio versions, bounded CSV staging and scenario snapshots."""
import csv
import io
import uuid
from copy import deepcopy
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .models import PortfolioImport, PortfolioRevision
from .portfolio_serializers import CSV_COLUMNS, MAX_ROWS, PortfolioInput, PortfolioLineInput


def projected(item):
    result = {'id': str(item.id), 'created_at': item.created_at.isoformat(),
              'project_id': str(item.project_id), 'lines': deepcopy(item.lines),
              'monthly_total': format(item.monthly_total, '.2f'), 'currency': 'USD'}
    return {**result, 'number': item.number} if isinstance(item, PortfolioRevision) else result


def normalized_lines(lines):
    return [{**line, 'id': str(uuid.uuid4())} for line in lines]


def total(lines):
    return sum((Decimal(line['monthly_cost']) for line in lines), Decimal(0))


def parse_csv(text):
    reader = csv.reader(io.StringIO(text.removeprefix('\ufeff'), newline=''), strict=True)
    try:
        header = next(reader, None)
        if header != list(CSV_COLUMNS):
            raise ValidationError({'csv': 'Expected exactly these columns in order: ' + ','.join(CSV_COLUMNS)})
        lines, errors = [], []
        for index, row in enumerate(reader, start=2):
            if index > MAX_ROWS + 1:
                raise ValidationError({'csv': 'CSV exceeds 1000 data rows.'})
            if len(row) != len(CSV_COLUMNS):
                errors.append({'row': index, 'errors': {'columns': ['Expected exactly five cells.']}})
                continue
            serializer = PortfolioLineInput(data=dict(zip(CSV_COLUMNS, row)))
            if serializer.is_valid():
                lines.append(serializer.validated_data)
            else:
                errors.append({'row': index, 'errors': serializer.errors})
    except csv.Error as exc:
        raise ValidationError({'csv': f'Malformed CSV near physical line {reader.line_num}.'}) from exc
    if errors:
        raise ValidationError({'rows': errors})
    serializer = PortfolioInput(data={'lines': lines})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data['lines']


def create_version(project, user, lines, source=None):
    latest = project.portfolio_revisions.order_by('-number').first()
    return PortfolioRevision.objects.create(project=project, created_by=user, lines=deepcopy(lines),
                                            number=latest.number + 1 if latest else 1,
                                            monthly_total=total(lines), source_import=source)


@transaction.atomic
def create_manual(org_id, project_id, user, lines):
    from .services import audit, membership, scoped_project
    org, _ = membership(org_id, user, write=True, lock=True)
    project = scoped_project(org, project_id)
    revision = create_version(project, user, normalized_lines(lines))
    audit(org, user, 'portfolio.created', revision, {'number': revision.number, 'line_count': len(lines)})
    return revision


@transaction.atomic
def preview_csv(org_id, project_id, user, text):
    from .services import audit, membership, scoped_project
    org, _ = membership(org_id, user, write=True, lock=True)
    project = scoped_project(org, project_id)
    lines = normalized_lines(parse_csv(text))
    preview = PortfolioImport.objects.create(project=project, created_by=user,
                                              lines=lines, monthly_total=total(lines))
    audit(org, user, 'portfolio.previewed', preview, {'line_count': len(lines)})
    return preview


@transaction.atomic
def confirm_import(org_id, project_id, import_id, user):
    from .services import audit, membership, scoped_project
    org, _ = membership(org_id, user, write=True, lock=True)
    project = scoped_project(org, project_id)
    preview = get_object_or_404(PortfolioImport, project=project, id=import_id)
    existing = PortfolioRevision.objects.filter(source_import=preview).first()
    if existing:
        return existing, False
    revision = create_version(project, user, preview.lines, preview)
    audit(org, user, 'portfolio.imported', revision, {'import_id': str(preview.id), 'number': revision.number})
    return revision, True


def scenario_context(project, data):
    context = {}
    if data.get('portfolio_revision_id'):
        item = get_object_or_404(PortfolioRevision, project=project, id=data['portfolio_revision_id'])
        if Decimal(data['inputs']['monthly_cost']) != item.monthly_total:
            raise ValidationError({'inputs': {'monthly_cost': 'Must equal the selected portfolio monthly total.'}})
        all_ids = [line['id'] for line in item.lines]
        selected = [str(value) for value in data.get('affected_line_ids', all_ids)]
        if not selected or len(selected) != len(set(selected)) or not set(selected).issubset(all_ids):
            raise ValidationError({'affected_line_ids': 'Select unique line IDs belonging to this portfolio revision.'})
        context = {'portfolio_revision_id': str(item.id), 'portfolio_number': item.number,
                   'lines': deepcopy(item.lines), 'monthly_total': format(item.monthly_total, '.2f'),
                   'currency': 'USD', 'affected_line_ids': selected}
    if data.get('evidence_revision_id'):
        from apps.evidence.services import get_published_snapshot
        context = {**context, 'evidence': get_published_snapshot(data['evidence_revision_id'])}
    return context
