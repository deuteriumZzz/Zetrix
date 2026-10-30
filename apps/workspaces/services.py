"""Transactional writes with tenant checks performed under an organization lock.

The organization lock serializes membership changes, revision creation and runs.
It provides a deliberately simple concurrency model for the first bounded slice.
"""
import hashlib
import json
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.scenario_engine.engine import calculate
from apps.scenario_engine.portfolio import calculate_portfolio
from .portfolio import scenario_context
from .api import Conflict
from .models import AuditEvent, Membership, Organization, Project, Scenario, ScenarioRevision, ScenarioRun


WRITE_ROLES = {'owner', 'admin', 'analyst'}


def audit(org, actor, action, resource, metadata=None):
    AuditEvent.objects.create(organization=org, actor=actor, action=action,
                              resource_id=resource.id, metadata=metadata or {})


def membership(org_id, user, write=False, lock=False):
    organizations = Organization.objects.all()
    if lock:
        organizations = organizations.select_for_update()
    org = get_object_or_404(organizations, id=org_id)
    member = get_object_or_404(Membership, organization=org, user=user, active=True)
    if write and member.role not in WRITE_ROLES:
        raise PermissionDenied('Your role is read-only.')
    return org, member


def scoped_project(org, project_id):
    return get_object_or_404(Project, organization=org, id=project_id)


def scoped_scenario(org, project_id, scenario_id):
    return get_object_or_404(Scenario, id=scenario_id, project_id=project_id,
                            project__organization=org)


@transaction.atomic
def create_organization(user, data):
    org = Organization.objects.create(**data)
    Membership.objects.create(organization=org, user=user, role='owner')
    audit(org, user, 'organization.created', org)
    return org


@transaction.atomic
def create_project(org_id, user, data):
    org, _ = membership(org_id, user, write=True, lock=True)
    item = Project.objects.create(organization=org, created_by=user, **data)
    audit(org, user, 'project.created', item)
    return item


@transaction.atomic
def create_scenario(org_id, project_id, user, data):
    org, _ = membership(org_id, user, write=True, lock=True)
    project = scoped_project(org, project_id)
    item = Scenario.objects.create(project=project, title=data['title'], created_by=user)
    ScenarioRevision.objects.create(scenario=item, number=1, inputs=deepcopy(data['inputs']),
                                    context=scenario_context(project, data), created_by=user)
    audit(org, user, 'scenario.created', item, {'revision': 1})
    return item


@transaction.atomic
def create_revision(org_id, project_id, scenario_id, user, data):
    org, _ = membership(org_id, user, write=True, lock=True)
    scenario = scoped_scenario(org, project_id, scenario_id)
    latest = scenario.revisions.order_by('-number').first()
    revision = ScenarioRevision.objects.create(scenario=scenario, number=latest.number + 1 if latest else 1,
                                               inputs=deepcopy(data['inputs']),
                                               context=scenario_context(scenario.project, data), created_by=user)
    audit(org, user, 'revision.created', revision, {'number': revision.number})
    return revision


@transaction.atomic
def create_run(org_id, user, revision_id, key):
    org, _ = membership(org_id, user, write=True, lock=True)
    revision = get_object_or_404(ScenarioRevision, id=revision_id, scenario__project__organization=org)
    # Keep legacy scalar fingerprints stable after adding optional context.
    payload = {'revision_id': str(revision.id), 'inputs': revision.inputs,
               **({'context': revision.context} if revision.context else {})}
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    existing = ScenarioRun.objects.filter(organization=org, idempotency_key=key).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise Conflict('Idempotency-Key was already used for another revision.')
        return existing, False
    inputs = deepcopy(revision.inputs)
    context = deepcopy(revision.context)
    results = calculate_portfolio(inputs, context) if context.get('portfolio_revision_id') else calculate(inputs)
    item = ScenarioRun.objects.create(organization=org, revision=revision, created_by=user,
                                     idempotency_key=key, request_fingerprint=fingerprint,
                                     inputs=inputs, context=context, results=results, engine_version=results['engine_version'],
                                     assumptions=deepcopy(results['assumptions']))
    audit(org, user, 'run.succeeded', item, {'engine_version': item.engine_version})
    return item, True


def require_member_admin(actor_member, target_role):
    if actor_member.role not in {'owner', 'admin'}:
        raise PermissionDenied('Only organization owners and admins can manage members.')
    if target_role == 'owner' and actor_member.role != 'owner':
        raise PermissionDenied('Only an owner can manage owner memberships.')


@transaction.atomic
def add_member(org_id, user, data):
    org, actor_member = membership(org_id, user, lock=True)
    require_member_admin(actor_member, data['role'])
    target = get_user_model().objects.filter(username=data['username'], is_active=True).first()
    if target is None:
        raise ValidationError({'username': 'No active account is available for this username.'})
    if Membership.objects.filter(organization=org, user=target).exists():
        raise Conflict('This account already has a membership; update the existing membership.')
    member = Membership.objects.create(organization=org, user=target, role=data['role'])
    audit(org, user, 'member.added', member, {'role': member.role})
    return member


@transaction.atomic
def update_member(org_id, member_id, user, data):
    org, actor_member = membership(org_id, user, lock=True)
    member = get_object_or_404(Membership.objects.select_related('user'), organization=org, id=member_id)
    require_member_admin(actor_member, member.role)
    next_role = data.get('role', member.role)
    next_active = data.get('active', member.active)
    require_member_admin(actor_member, next_role)
    if member.active and member.role == 'owner' and (not next_active or next_role != 'owner'):
        owners = Membership.objects.filter(organization=org, active=True, role='owner').count()
        if owners <= 1:
            raise Conflict('An organization must retain at least one active owner.')
    # Copy-on-write values applied as one update, rather than piecemeal model mutation.
    Membership.objects.filter(pk=member.pk).update(role=next_role, active=next_active)
    updated = Membership.objects.select_related('user').get(pk=member.pk)
    audit(org, user, 'member.updated', updated, {'role': next_role, 'active': next_active})
    return updated


@transaction.atomic
def export_run(org_id, run_id, user):
    org, _ = membership(org_id, user, write=True, lock=True)
    item = get_object_or_404(ScenarioRun, organization=org, id=run_id)
    audit(org, user, 'run.exported', item)
    return item
