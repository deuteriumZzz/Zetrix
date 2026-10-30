"""Only bounded plain text and unique run references cross the API boundary."""
from rest_framework import serializers
from apps.workspaces.serializers import StrictSerializer


class TextInput(serializers.CharField):
    def to_internal_value(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError('Use text.')
        result = super().to_internal_value(value)
        if any(ord(char) < 32 and char not in '\n\r\t' for char in result):
            raise serializers.ValidationError('Unsupported control character.')
        return result


class DecisionInput(StrictSerializer):
    title = TextInput(max_length=160)
    note = TextInput(max_length=4000)
    run_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=3)

    def validate_run_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Choose distinct runs.')
        return value


def projected(item):
    return {'id': str(item.id), 'created_at': item.created_at.isoformat(),
            'project_id': str(item.project_id), 'title': item.title, 'note': item.note,
            'run_ids': item.run_ids, 'snapshots': item.snapshots}
