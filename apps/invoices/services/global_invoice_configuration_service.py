from django.core.cache import cache
from django.db import transaction
from apps.invoices.models.configuration import GlobalInvoiceConfiguration
from apps.invoices.forms.configuration_form import GlobalInvoiceConfigurationForm
from apps.core.services.base import BaseService

class GlobalInvoiceConfigurationService(BaseService):
    CACHE_KEY = "global_invoice_configuration"
    
    @classmethod
    def get_active_configuration(cls) -> GlobalInvoiceConfiguration:
        """
        Retrieves the singleton Global Invoice Configuration safely.
        Caches the configuration to prevent unnecessary DB queries.
        """
        config = cache.get(cls.CACHE_KEY)
        if config is None:
            config = GlobalInvoiceConfiguration.get_config()
            cache.set(cls.CACHE_KEY, config, timeout=3600 * 24) # Cache for 24 hours
        return config

    @classmethod
    @transaction.atomic
    def update_configuration(cls, post_data: dict, updated_by_id=None) -> tuple[bool, dict]:
        """
        Validates and updates the configuration.
        Invalidates the cache on success.
        Returns a tuple: (success, result)
        Where result is either the saved config or a dictionary of form errors.
        """
        config = cls.get_active_configuration()
        form = GlobalInvoiceConfigurationForm(post_data, instance=config)
        
        if form.is_valid():
            # If we wanted to track updated_by manually, we could update the model fields here
            saved_config = form.save()
            # Clear cache
            cls.clear_cache()
            return True, saved_config
            
        return False, form.errors

    @classmethod
    def clear_cache(cls):
        """Invalidates the active configuration cache."""
        cache.delete(cls.CACHE_KEY)
