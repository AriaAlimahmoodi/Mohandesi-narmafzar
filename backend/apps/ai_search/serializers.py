from rest_framework import serializers

from apps.ai_search.models import AISearchQuery, AISearchCitation


class AISearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
    )


class AISearchCitationSerializer(serializers.ModelSerializer):
    resource_id = serializers.SerializerMethodField()
    resource_file_id = serializers.SerializerMethodField()
    chunk_id = serializers.SerializerMethodField()

    def get_resource_id(self, obj):
        return obj.resource_id

    def get_resource_file_id(self, obj):
        return obj.resource_file_id

    def get_chunk_id(self, obj):
        return obj.chunk_id

    class Meta:
        model = AISearchCitation
        fields = (
            "id",
            "resource_id",
            "resource_title",
            "resource_file_id",
            "resource_file_version",
            "chunk_id",
            "page_number",
            "relevance_score",
            "excerpt",
            "created_at",
        )


class AISearchHistoryListSerializer(serializers.ModelSerializer):
    results_count = serializers.SerializerMethodField()

    def get_results_count(self, obj):
        return obj.citations.count()

    class Meta:
        model = AISearchQuery
        fields = (
            "id",
            "query",
            "status",
            "created_at",
            "results_count",
        )

    class Meta:
        model = AISearchCitation
        fields = (
            "id",
            "resource_id",
            "resource_title",
            "resource_file_id",
            "resource_file_version",
            "chunk_id",
            "page_number",
            "relevance_score",
            "excerpt",
            "created_at",
        )


class AISearchHistoryListSerializer(serializers.ModelSerializer):
    results_count = serializers.IntegerField(
        source="citations.count",
        read_only=True,
    )

    class Meta:
        model = AISearchQuery
        fields = (
            "id",
            "query",
            "status",
            "created_at",
            "results_count",
        )


class AISearchHistoryDetailSerializer(serializers.ModelSerializer):
    citations = AISearchCitationSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = AISearchQuery
        fields = (
            "id",
            "query",
            "response",
            "status",
            "created_at",
            "citations",
        )