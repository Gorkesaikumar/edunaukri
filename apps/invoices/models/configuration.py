from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models.base import AuditedBaseModel
from apps.core.validators.common import validate_gst, validate_pan, validate_phone, validate_organization_name

class GlobalInvoiceConfiguration(AuditedBaseModel):
    """Singleton model to store global invoice settings."""
    
    # Business Details
    business_name = models.CharField(max_length=255, default="EduNaukri", validators=[validate_organization_name])
    invoice_header = models.CharField(max_length=100, default="TAX INVOICE")
    business_address = models.TextField(default="EduNaukri Business Address")
    gstin = models.CharField(max_length=50, blank=True, validators=[validate_gst])
    pan = models.CharField(max_length=50, blank=True, validators=[validate_pan])
    phone = models.CharField(max_length=50, blank=True, validators=[validate_phone])
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Content
    footer_text = models.TextField(blank=True)
    thank_you_message = models.CharField(max_length=255, default="Thank you for choosing EduNaukri.")
    terms_conditions = models.TextField(blank=True)
    payment_notes = models.TextField(blank=True)

    # Billing Configuration
    pricing_method = models.CharField(
        max_length=50, 
        choices=[('percentage_ctc', 'Percentage of Annual CTC'), ('fixed_fee', 'Fixed Recruitment Fee')], 
        default='percentage_ctc'
    )
    service_charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('8.33'), validators=[MinValueValidator(0)])
    fixed_recruitment_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    gst_enabled = models.BooleanField(default=True)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'), validators=[MinValueValidator(0)])
    tax_calculation_mode = models.CharField(
        max_length=50, 
        choices=[('cgst_sgst', 'CGST + SGST'), ('igst', 'IGST')], 
        default='cgst_sgst'
    )
    payment_due_days = models.PositiveIntegerField(default=7)
    currency = models.CharField(max_length=10, default='INR')

    # Visibility Flags
    show_gstin = models.BooleanField(default=True)
    show_pan = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=True)
    show_email = models.BooleanField(default=True)
    show_website = models.BooleanField(default=True)
    show_coupon_discount = models.BooleanField(default=True)
    show_tax_breakdown = models.BooleanField(default=True)
    show_payment_method = models.BooleanField(default=True)
    show_transaction_id = models.BooleanField(default=True)
    show_subscription_validity = models.BooleanField(default=True)
    show_terms = models.BooleanField(default=True)

    class Meta:
        db_table = "billing_invoice_configuration"
        verbose_name = "Global Invoice Configuration"
        verbose_name_plural = "Global Invoice Configuration"

    @classmethod
    def get_config(cls):
        """Get the singleton configuration instance. Does not cache internally (use Service for caching)."""
        config, created = cls.objects.get_or_create(id=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1  # Force singleton
        super().save(*args, **kwargs)
        # Invalidate cache on save
        from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService
        GlobalInvoiceConfigurationService.clear_cache()
