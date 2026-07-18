from apps.core.repositories.crud import CRUDRepository
from apps.invoices.models import (
    Invoice,
    InvoiceLineItem,
    InvoiceStatusHistory,
    PaymentRecord,
    RefundRecord,
)


class InvoiceRepository(CRUDRepository):
    model = Invoice


class InvoiceLineItemRepository(CRUDRepository):
    model = InvoiceLineItem


class PaymentRecordRepository(CRUDRepository):
    model = PaymentRecord


class InvoiceStatusHistoryRepository(CRUDRepository):
    model = InvoiceStatusHistory


class RefundRecordRepository(CRUDRepository):
    model = RefundRecord
