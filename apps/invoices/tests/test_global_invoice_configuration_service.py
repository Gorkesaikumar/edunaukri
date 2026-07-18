import pytest
from decimal import Decimal
from django.core.cache import cache
from apps.invoices.models.configuration import GlobalInvoiceConfiguration
from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService

@pytest.mark.django_db
class TestGlobalInvoiceConfigurationService:
    def setup_method(self):
        cache.clear()
        GlobalInvoiceConfiguration.objects.all().delete()
        self.config = GlobalInvoiceConfiguration.get_config()

    def test_get_active_configuration_caches_result(self):
        # Fetching for the first time should cache it
        cached_config = GlobalInvoiceConfigurationService.get_active_configuration()
        assert cache.get(GlobalInvoiceConfigurationService.CACHE_KEY) == cached_config

    def test_update_configuration_invalidates_cache(self):
        # Ensure it's cached
        GlobalInvoiceConfigurationService.get_active_configuration()
        assert cache.get(GlobalInvoiceConfigurationService.CACHE_KEY) is not None
        
        # Update via service
        data = {
            "business_name": "New Test Business",
            "pricing_method": "percentage_ctc",
            "service_charge_percentage": "10.00",
            "fixed_recruitment_fee": "0.00",
            "gst_percentage": "18.00",
            "tax_calculation_mode": "cgst_sgst",
            "payment_due_days": 15,
            "currency": "INR",
            "show_gstin": True,
            "show_phone": True,
            "show_email": True,
            "show_website": True,
            "show_coupon_discount": True,
            "show_tax_breakdown": True,
            "show_payment_method": True,
            "show_transaction_id": True,
            "show_subscription_validity": True,
            "show_terms": True,
        }
        
        success, result = GlobalInvoiceConfigurationService.update_configuration(data)
        assert success is True
        
        # Cache should be invalidated (empty)
        assert cache.get(GlobalInvoiceConfigurationService.CACHE_KEY) is None
        
        # Fetching again should get the new name
        new_config = GlobalInvoiceConfigurationService.get_active_configuration()
        assert new_config.business_name == "New Test Business"
        assert new_config.service_charge_percentage == Decimal("10.00")
