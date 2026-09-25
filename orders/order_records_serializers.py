from rest_framework import serializers


class OrderRecordListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_id = serializers.CharField(allow_null=True)
    ss_party_name = serializers.CharField(allow_blank=True)
    ss_user_name = serializers.CharField(allow_blank=True)
    crm_name = serializers.CharField(allow_blank=True)
    total_amount = serializers.CharField()
    status = serializers.CharField(allow_blank=True)
    verification_status = serializers.CharField(allow_null=True)
    punched = serializers.BooleanField(allow_null=True)
    items_count = serializers.IntegerField()
    verified_items_count = serializers.IntegerField()
    dispatched_items_count = serializers.IntegerField()
    dispatched_quantity = serializers.IntegerField()
    dispatch_status = serializers.CharField()
    created_at = serializers.CharField()


class OrderRecordDetailSerializer(serializers.Serializer):
    """
    Complete order detail serializer.
    """

    order_id = serializers.CharField(allow_null=True)

    total_amount = serializers.CharField()

    status = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField()

    ss_user = serializers.DictField()
    crm_user = serializers.DictField()

    verification = serializers.DictField(allow_null=True)

    summary = serializers.DictField()

    items = serializers.ListField(
        child=serializers.DictField()
    )

    note = serializers.CharField(
        allow_blank=True,
        allow_null=True
    )

    notes = serializers.CharField(
        allow_blank=True,
        allow_null=True
    )