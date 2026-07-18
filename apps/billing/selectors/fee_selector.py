from django.db.models import Q
from django.utils import timezone

from apps.billing.constants.enums import FeeScopeType
from apps.billing.models import FeeSchedule, PlacementFee
from apps.core.constants.enums import EntityReferenceType
from apps.core.selectors.read import ReadSelector


class FeeScheduleSelector(ReadSelector):
    model = FeeSchedule

    def list_by_domain(self, domain: str | None = None):
        queryset = self.list_all(order_by="-effective_from")
        if domain:
            queryset = queryset.filter(domain=domain)
        return queryset

    def _active_queryset(self, domain: str):
        now = timezone.now()
        return (
            self.filter_by(domain=domain, is_active=True)
            .filter(effective_from__lte=now)
            .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=now))
        )

    def active_for_domain(self, domain: str) -> FeeSchedule | None:
        return self._active_queryset(domain).order_by("-effective_from").first()

    def active_for_placement(
        self,
        domain: str,
        *,
        bill_to_entity_type: str | None = None,
        bill_to_entity_id=None,
    ) -> FeeSchedule | None:
        """Resolve the most specific active fee schedule for a placement."""
        queryset = self._active_queryset(domain)
        scoped_candidates: list[tuple[str, object | None]] = []

        if bill_to_entity_type == EntityReferenceType.IT_COMPANY and bill_to_entity_id:
            scoped_candidates.append((FeeScopeType.COMPANY, bill_to_entity_id))
        elif (
            bill_to_entity_type == EntityReferenceType.FACULTY_COLLEGE
            and bill_to_entity_id
        ):
            scoped_candidates.append((FeeScopeType.COLLEGE, bill_to_entity_id))

        for scope_type, scope_id in scoped_candidates:
            match = (
                queryset.filter(scope_type=scope_type, scope_id=scope_id)
                .order_by("-effective_from")
                .first()
            )
            if match:
                return match

        return (
            queryset.filter(scope_type=FeeScopeType.GLOBAL, scope_id__isnull=True)
            .order_by("-effective_from")
            .first()
        )


class PlacementFeeSelector(ReadSelector):
    model = PlacementFee

    def list_by_domain(self, domain: str | None = None):
        queryset = self.list_all(order_by="-created_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        return queryset

    def get_active(self, fee_id):
        return self.filter_by(pk=fee_id).first()
