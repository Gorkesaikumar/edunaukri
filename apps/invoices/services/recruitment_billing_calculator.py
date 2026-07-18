from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService

@dataclass(frozen=True)
class BillingCalculationResult:
    pricing_method: str
    service_charge_percentage: Decimal
    candidate_annual_ctc: Decimal
    taxable_amount: Decimal
    gst_enabled: bool
    gst_percentage: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax_amount: Decimal
    grand_total: Decimal
    currency: str

class RecruitmentBillingCalculator:
    """Centralized service for calculating recruitment fees based on global config."""

    def __init__(self):
        # Load the singleton active configuration
        self.config = GlobalInvoiceConfigurationService.get_active_configuration()

    def calculate(self, annual_ctc: Decimal) -> BillingCalculationResult:
        if not annual_ctc or annual_ctc <= 0:
            raise ValueError("Candidate Annual CTC must be greater than zero to calculate recruitment billing.")

        # Resolve pricing method and taxable amount
        pricing_method = self.config.pricing_method
        service_charge_percentage = self.config.service_charge_percentage
        
        if pricing_method == 'percentage_ctc':
            # Recruitment Fee = Annual CTC × Service Charge Percentage / 100
            taxable_amount = (annual_ctc * service_charge_percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif pricing_method == 'fixed_fee':
            taxable_amount = self.config.fixed_recruitment_fee
        else:
            raise ValueError(f"Unknown pricing method: {pricing_method}")

        # Tax Calculation
        gst_enabled = self.config.gst_enabled
        gst_percentage = self.config.gst_percentage
        tax_calculation_mode = self.config.tax_calculation_mode

        cgst = Decimal('0.00')
        sgst = Decimal('0.00')
        igst = Decimal('0.00')
        total_tax = Decimal('0.00')

        if gst_enabled and gst_percentage > 0:
            total_tax = (taxable_amount * gst_percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if tax_calculation_mode == 'cgst_sgst':
                # Split evenly
                half_tax = (total_tax / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                cgst = half_tax
                sgst = total_tax - cgst  # Ensure rounding remainder is absorbed correctly
            elif tax_calculation_mode == 'igst':
                igst = total_tax

        grand_total = taxable_amount + total_tax

        return BillingCalculationResult(
            pricing_method=pricing_method,
            service_charge_percentage=service_charge_percentage,
            candidate_annual_ctc=annual_ctc,
            taxable_amount=taxable_amount,
            gst_enabled=gst_enabled,
            gst_percentage=gst_percentage,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            total_tax_amount=total_tax,
            grand_total=grand_total,
            currency=self.config.currency
        )
