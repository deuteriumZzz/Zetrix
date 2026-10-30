"""Bounded inputs; URLs are metadata and are never fetched by this service."""
from urllib.parse import urlsplit
from rest_framework import serializers
from apps.workspaces.serializers import StrictSerializer, validated


class SourceInput(StrictSerializer):
    publisher = serializers.CharField(max_length=200)
    url = serializers.URLField(max_length=2000)
    allowed_use = serializers.CharField(max_length=1000)

    def validate_url(self, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            raise serializers.ValidationError('Use an HTTP(S) URL without embedded credentials.')
        return value


class RevisionInput(StrictSerializer):
    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=2000)
    event_kind = serializers.ChoiceField(choices=['trade_restriction', 'supply_disruption', 'energy_shock', 'other'])
    country_codes = serializers.ListField(child=serializers.RegexField(r'^[A-Z]{2}$'), min_length=1, max_length=30)
    effective_at = serializers.DateTimeField()
    source_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=10)
    provenance = serializers.CharField(max_length=1000)

    def validate(self, attrs):
        for key in ('country_codes', 'source_ids'):
            if len(attrs[key]) != len(set(attrs[key])):
                raise serializers.ValidationError({key: 'Duplicate values are not allowed.'})
        return attrs


class PublishInput(StrictSerializer):
    revision_id = serializers.UUIDField()


class RevokeInput(StrictSerializer):
    reason = serializers.CharField(max_length=1000)
