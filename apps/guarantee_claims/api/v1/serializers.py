from rest_framework import serializers

from apps.guarantee_claims.constants.enums import ClaimResolution, ClaimType
from apps.guarantee_claims.models import GuaranteeClaim


class GuaranteeClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteeClaim
        fields = (
            "id",
            "claim_number",
            "domain",
            "guarantee_id",
            "application_entity_type",
            "application_entity_id",
            "placement_fee_id",
            "invoice_id",
            "claim_type",
            "status",
            "resolution",
            "reason",
            "exit_date",
            "submitted_at",
            "resolved_at",
            "approval_date",
            "approved_by_id",
            "review_notes",
            "supporting_documents",
            "created_at",
        )
        read_only_fields = fields


class GuaranteeClaimCreateSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(
        choices=GuaranteeClaim._meta.get_field("domain").choices
    )
    application_entity_type = serializers.CharField(max_length=40)
    application_entity_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField()
    claim_type = serializers.ChoiceField(choices=ClaimType.choices)
    reason = serializers.CharField()
    exit_date = serializers.DateField(required=False, allow_null=True)
    supporting_documents = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    placement_fee_id = serializers.UUIDField(required=False, allow_null=True)


class GuaranteeClaimStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=GuaranteeClaim._meta.get_field("status").choices
    )
    review_notes = serializers.CharField(required=False, allow_blank=True)


class GuaranteeClaimApproveSerializer(serializers.Serializer):
    resolution = serializers.ChoiceField(choices=ClaimResolution.choices)
    review_notes = serializers.CharField(required=False, allow_blank=True)


class GuaranteeClaimRejectSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)


class GuaranteeClaimResolveSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)
