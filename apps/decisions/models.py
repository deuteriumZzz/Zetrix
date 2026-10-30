"""Decision notes retain the exact compared run snapshots forever."""
from django.conf import settings
from django.db import models
from apps.workspaces.models import AppendOnlyRecord, Organization, Project


class Decision(AppendOnlyRecord):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='decisions')
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='decisions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=160)
    note = models.TextField(max_length=4000)
    run_ids = models.JSONField()
    snapshots = models.JSONField()
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)

    class Meta(AppendOnlyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['organization', 'idempotency_key'],
                                                name='decision_unique_org_key')]
