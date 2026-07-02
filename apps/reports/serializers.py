from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    requested_by_username = serializers.CharField(source="requested_by.username", read_only=True)

    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "status", "file", "generated_at")

    def get_file_url(self, obj) -> str | None:
        if obj.file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ("title", "country", "region", "market_type", "date_from", "date_to", "format")
