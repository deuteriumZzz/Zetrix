"""Tenant-locked immutable decisions and stored-run CSV generation."""
import csv
import hashlib
import io
import json
from copy import deepcopy
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from apps.workspaces.api import Conflict
from apps.workspaces.models import ScenarioRun
from apps.workspaces.presentation import run as present_run
from apps.workspaces.services import audit, membership
from .models import Decision


def comparison_key(run):
    """Different cost categories or portfolio baselines are not comparable."""
    return (run.revision.scenario.project_id, run.inputs['currency'], run.inputs['months'],
            Decimal(run.results['baseline_total']), run.inputs['kind'],
            run.context.get('portfolio_revision_id'))


def compatible_runs(org, ids):
    queryset = ScenarioRun.objects.select_related('revision__scenario').filter(organization=org)
    runs = [get_object_or_404(queryset, id=run_id) for run_id in ids]
    if any(run.status != 'succeeded' for run in runs):
        raise ValidationError({'run_ids': 'Only successful runs can be recorded.'})
    if len({comparison_key(run) for run in runs}) != 1:
        raise ValidationError({'run_ids': 'Runs must share project, currency, horizon, baseline cost, scenario kind and portfolio revision.'})
    return runs


@transaction.atomic
def create_decision(org_id, user, data, key):
    org, _ = membership(org_id, user, write=True, lock=True)
    payload = {**data, 'run_ids': [str(value) for value in data['run_ids']]}
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    existing = Decision.objects.filter(organization=org, idempotency_key=key).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise Conflict('Idempotency-Key was already used for another decision.')
        return existing, False
    runs = compatible_runs(org, payload['run_ids'])
    item = Decision.objects.create(
        organization=org, project_id=runs[0].revision.scenario.project_id,
        created_by=user, **payload, idempotency_key=key, request_fingerprint=fingerprint,
        snapshots=[deepcopy(present_run(run)) for run in runs])
    audit(org, user, 'decision.created', item, {'run_count': len(runs)})
    return item, True


def safe_cell(value):
    """Prefix suspicious spreadsheet formulas/control prefixes as literal text."""
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def render_csv(run):
    """A self-contained snapshot; no recalculation or current portfolio lookup."""
    output = io.StringIO(newline='')
    writer = csv.writer(output)

    def row(values):
        writer.writerow([safe_cell(value) for value in values])

    row(['section', 'field', 'value'])
    for key, value in (('run_id', run.id), ('created_at', run.created_at.isoformat()),
                       ('revision_id', run.revision_id), ('engine_version', run.engine_version)):
        row(['metadata', key, value])
    for key, value in run.inputs.items():
        row(['input', key, value])
    for key, value in run.results.items():
        if not isinstance(value, (dict, list)):
            row(['result', key, value])
    for index, assumption in enumerate(run.assumptions, start=1):
        row(['assumption', index, assumption])
    row(['context', 'snapshot_json', json.dumps(run.context, ensure_ascii=False, sort_keys=True)])
    lines = {line['id']: line for line in run.context.get('lines', [])}
    impacts = run.results.get('line_impacts', [])
    if impacts:
        row([])
        row(['line_id', 'supplier', 'country_code', 'category', 'affected', 'currency',
             'baseline_total', 'additional_total', 'scenario_total'])
        for impact in impacts:
            line = lines.get(impact['line_id'], {})
            row([impact['line_id'], line.get('supplier', ''), line.get('country_code', ''),
                 line.get('category', ''), impact['affected'], run.inputs['currency'],
                 impact['baseline_total'], impact['additional_total'], impact['scenario_total']])
    return output.getvalue()


@transaction.atomic
def export_csv(org_id, run_id, user):
    org, _ = membership(org_id, user, write=True, lock=True)
    run = get_object_or_404(ScenarioRun, organization=org, id=run_id)
    content = render_csv(run)
    audit(org, user, 'run.csv_exported', run)
    return content
