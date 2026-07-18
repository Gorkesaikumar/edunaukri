import io
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa
from apps.invoices.models import Invoice
from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService

class InvoiceRenderingService:
    """Service to render invoices as HTML or PDF."""

    def __init__(self, invoice: Invoice):
        self.invoice = invoice

    def get_rendering_context(self) -> dict:
        config = GlobalInvoiceConfigurationService.get_active_configuration()
        
        # Load line items and payments
        line_items = self.invoice.line_items.all()
        payments = self.invoice.payments.all()

        return {
            "invoice": self.invoice,
            "line_items": line_items,
            "payments": payments,
            "config": config,
            "generated_at": timezone.now(),
        }

    def render_html(self, template_name="invoices/invoice_template.html") -> str:
        context = self.get_rendering_context()
        return render_to_string(template_name, context)

    def render_pdf(self, template_name="invoices/invoice_template.html") -> bytes:
        html = self.render_html(template_name)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            return result.getvalue()
        return b""
