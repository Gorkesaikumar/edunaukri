from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.core.constants.enums import EntityReferenceType
from apps.core.selectors.read import ReadSelector
from apps.invoices.constants.enums import InvoiceStatus
from apps.invoices.models import Invoice


OUTSTANDING_STATUSES = (
    InvoiceStatus.DRAFT,
    InvoiceStatus.PENDING,
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.OVERDUE,
)


class InvoiceSelector(ReadSelector):
    model = Invoice

    def list_by_domain(self, domain: str | None = None):
        queryset = self.list_all(order_by="-created_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        return queryset

    def get_active(self, invoice_id):
        return self.filter_by(pk=invoice_id).first()

    def for_company_ids(
        self, company_ids, *, domain: str | None = None, status: str | None = None
    ):
        queryset = self.filter_by(
            bill_to_entity_type=EntityReferenceType.IT_COMPANY,
            bill_to_entity_id__in=company_ids,
        ).order_by("-created_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def for_college_ids(
        self, college_ids, *, domain: str | None = None, status: str | None = None
    ):
        queryset = self.filter_by(
            bill_to_entity_type=EntityReferenceType.FACULTY_COLLEGE,
            bill_to_entity_id__in=college_ids,
        ).order_by("-created_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def search(
        self,
        *,
        domain: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        bill_to_entity_type: str | None = None,
        bill_to_entity_ids=None,
        q: str | None = None,
        issued_from=None,
        issued_to=None,
        ordering: str = "-created_at",
    ):
        queryset = self.list_all(order_by=ordering)
        if domain:
            queryset = queryset.filter(domain=domain)
        if status:
            queryset = queryset.filter(status=status)
        if bill_to_entity_type:
            queryset = queryset.filter(bill_to_entity_type=bill_to_entity_type)
        if bill_to_entity_ids is not None:
            queryset = queryset.filter(bill_to_entity_id__in=bill_to_entity_ids)
        if q:
            queryset = queryset.filter(
                Q(invoice_number__icontains=q) | Q(bill_to_name_snapshot__icontains=q)
            )
        if issued_from:
            queryset = queryset.filter(issued_at__gte=issued_from)
        if issued_to:
            queryset = queryset.filter(issued_at__lte=issued_to)
        if payment_status == "paid":
            queryset = queryset.filter(status=InvoiceStatus.PAID)
        elif payment_status == "outstanding":
            queryset = queryset.filter(status__in=OUTSTANDING_STATUSES)
        elif payment_status == "overdue":
            queryset = queryset.filter(status=InvoiceStatus.OVERDUE)
        return queryset


class OutstandingInvoiceSelector(ReadSelector):
    model = Invoice

    def list(self, *, domain: str | None = None, bill_to_entity_ids=None):
        queryset = self.filter_by(status__in=OUTSTANDING_STATUSES).order_by(
            "due_at", "-created_at"
        )
        if domain:
            queryset = queryset.filter(domain=domain)
        if bill_to_entity_ids is not None:
            queryset = queryset.filter(bill_to_entity_id__in=bill_to_entity_ids)
        now = timezone.now()
        return queryset.filter(
            Q(due_at__isnull=True)
            | Q(due_at__gte=now)
            | Q(status=InvoiceStatus.OVERDUE)
        )

    def due_for_overdue_marking(self):
        now = timezone.now()
        return self.filter_by(
            status__in=(
                InvoiceStatus.ISSUED,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.PENDING,
            ),
            due_at__lt=now,
        ).order_by("due_at")


class PaidInvoiceSelector(ReadSelector):
    model = Invoice

    def list(self, *, domain: str | None = None, bill_to_entity_ids=None):
        queryset = self.filter_by(status=InvoiceStatus.PAID).order_by("-paid_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if bill_to_entity_ids is not None:
            queryset = queryset.filter(bill_to_entity_id__in=bill_to_entity_ids)
        return queryset


class FinancialStatisticsSelector(ReadSelector):
    model = Invoice

    def summary(self, *, domain: str | None = None, bill_to_entity_ids=None) -> dict:
        queryset = self.filter_by(is_deleted=False)
        if domain:
            queryset = queryset.filter(domain=domain)
        if bill_to_entity_ids is not None:
            queryset = queryset.filter(bill_to_entity_id__in=bill_to_entity_ids)

        aggregates = queryset.aggregate(
            total_invoiced=Sum("total_amount"),
            total_paid=Sum("amount_paid"),
            invoice_count=Count("id"),
        )
        outstanding_qs = queryset.filter(status__in=OUTSTANDING_STATUSES)
        outstanding = outstanding_qs.aggregate(
            outstanding_amount=Sum(F("total_amount") - F("amount_paid")),
            outstanding_count=Count("id"),
        )
        overdue_count = queryset.filter(status=InvoiceStatus.OVERDUE).count()
        paid_count = queryset.filter(status=InvoiceStatus.PAID).count()
        refunded_count = queryset.filter(status=InvoiceStatus.REFUNDED).count()

        total_invoiced = aggregates["total_invoiced"] or 0
        total_paid = aggregates["total_paid"] or 0
        outstanding_amount = outstanding["outstanding_amount"] or 0

        return {
            "total_invoiced": str(total_invoiced),
            "total_paid": str(total_paid),
            "total_outstanding": str(outstanding_amount),
            "invoice_count": aggregates["invoice_count"] or 0,
            "outstanding_count": outstanding["outstanding_count"] or 0,
            "overdue_count": overdue_count,
            "paid_count": paid_count,
            "refunded_count": refunded_count,
        }
