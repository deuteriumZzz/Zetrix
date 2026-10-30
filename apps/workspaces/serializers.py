"""Strict API contracts: reject unknown keys instead of silently ignoring them."""
from collections.abc import Mapping
from rest_framework import serializers
from apps.scenario_engine.engine import calculate
from .models import Membership


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: 'Unknown field.' for key in sorted(unknown)})
        return super().to_internal_value(data)


class OrganizationInput(StrictSerializer):
    name = serializers.CharField(max_length=160)


class ProjectInput(StrictSerializer):
    title = serializers.CharField(max_length=160)
    currency = serializers.ChoiceField(choices=['USD'], default='USD')


class RevisionInput(StrictSerializer):
    inputs = serializers.JSONField()
    portfolio_revision_id = serializers.UUIDField(required=False)
    affected_line_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=1000, required=False)
    evidence_revision_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if 'affected_line_ids' in attrs and 'portfolio_revision_id' not in attrs:
            raise serializers.ValidationError({'affected_line_ids': 'Requires portfolio_revision_id.'})
        return attrs

    def validate_inputs(self, value):
        try:
            if isinstance(value, dict):
                for field in ('monthly_cost', 'exposure', 'shock'):
                    if not isinstance(value.get(field), str):
                        raise ValueError(f'{field}: API values must be decimal strings.')
            calculate(value)
        except (ValueError, TypeError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class ScenarioInput(RevisionInput):
    title = serializers.CharField(max_length=160)


class RunInput(StrictSerializer):
    revision_id = serializers.UUIDField()


class LoginInput(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class MemberInput(StrictSerializer):
    username = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=Membership.ROLES)


class MemberUpdate(StrictSerializer):
    role = serializers.ChoiceField(choices=Membership.ROLES, required=False)
    active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Provide role or active.')
        return attrs


def validated(schema, data):
    serializer = schema(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
