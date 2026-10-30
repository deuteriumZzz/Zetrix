"""Tenant-owned scenario records. No destructive API is exposed for history."""
import uuid

from django.conf import settings
from django.db import models


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['created_at', 'id']


class Organization(Record):
    name = models.CharField(max_length=160)


class Membership(Record):
    ROLES = [(role, role) for role in ('owner', 'admin', 'analyst', 'viewer')]
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=16, choices=ROLES)
    active = models.BooleanField(default=True)

    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['organization', 'user'], name='workspace_unique_member')]


class Project(Record):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='projects')
    title = models.CharField(max_length=160)
    currency = models.CharField(max_length=3, default='USD')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Scenario(Record):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='scenarios')
    title = models.CharField(max_length=160)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError('Historical records are append-only.')

    def delete(self):
        raise ValueError('Historical records are append-only.')


class AppendOnlyRecord(Record):
    """Guard instance and QuerySet writes; database administrators remain trusted."""
    objects = AppendOnlyQuerySet.as_manager()
    class Meta(Record.Meta):
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self._state.adding or force_update or update_fields is not None:
            raise ValueError('Historical records are append-only.')
        return super().save(force_insert=True, using=using)

    def delete(self, *args, **kwargs):
        raise ValueError('Historical records are append-only.')


class ScenarioRevision(AppendOnlyRecord):
    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    inputs = models.JSONField()
    context = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['scenario', 'number'], name='workspace_unique_revision')]


class ScenarioRun(AppendOnlyRecord):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='runs')
    revision = models.ForeignKey(ScenarioRevision, on_delete=models.PROTECT, related_name='runs')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='succeeded')
    inputs = models.JSONField()
    context = models.JSONField(default=dict)
    results = models.JSONField()
    engine_version = models.CharField(max_length=64)
    assumptions = models.JSONField()

    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['organization', 'idempotency_key'], name='workspace_unique_run_key')]


class AuditEvent(AppendOnlyRecord):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=64)
    resource_id = models.UUIDField()
    metadata = models.JSONField(default=dict)


class PortfolioImport(AppendOnlyRecord):
    """Validated, immutable CSV preview; confirmation references it once."""
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='portfolio_imports')
    lines = models.JSONField()
    monthly_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class PortfolioRevision(AppendOnlyRecord):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='portfolio_revisions')
    number = models.PositiveIntegerField()
    lines = models.JSONField()
    monthly_total = models.DecimalField(max_digits=12, decimal_places=2)
    source_import = models.OneToOneField(PortfolioImport, null=True, blank=True,
                                         on_delete=models.PROTECT, related_name='confirmed_revision')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['project', 'number'], name='workspace_unique_portfolio_revision')]
