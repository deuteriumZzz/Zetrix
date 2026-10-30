"""Curated public evidence. Sources, revisions and publication decisions are append-only."""
from django.conf import settings
from django.db import models
from apps.workspaces.models import AppendOnlyRecord, Record


class EvidenceSource(AppendOnlyRecord):
    publisher = models.CharField(max_length=200)
    url = models.URLField(max_length=2000)
    allowed_use = models.CharField(max_length=1000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Event(Record):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_revision = models.ForeignKey('EventRevision', null=True, blank=True,
                                          on_delete=models.PROTECT, related_name='+')


class EventRevision(AppendOnlyRecord):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=2000)
    event_kind = models.CharField(max_length=32)
    country_codes = models.JSONField()
    effective_at = models.DateTimeField()
    provenance = models.CharField(max_length=1000)
    sources = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['event', 'number'], name='evidence_unique_revision')]


class Publication(AppendOnlyRecord):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='publications')
    revision = models.ForeignKey(EventRevision, on_delete=models.PROTECT, related_name='publications')
    action = models.CharField(max_length=16, choices=[('publish', 'publish'), ('revoke', 'revoke')])
    reason = models.CharField(max_length=1000, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
