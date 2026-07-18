from django import forms
from apps.invoices.models.configuration import GlobalInvoiceConfiguration

class GlobalInvoiceConfigurationForm(forms.ModelForm):
    class Meta:
        model = GlobalInvoiceConfiguration
        fields = "__all__"
        widgets = {
            "business_address": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-lg border-outline-variant/50 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all"}),
            "footer_text": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-lg border-outline-variant/50 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-lg border-outline-variant/50 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all"}),
            "payment_notes": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-lg border-outline-variant/50 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all"}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-full rounded-lg border-outline-variant/50 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all'
            else:
                field.widget.attrs['class'] = 'rounded border-outline-variant/50 text-primary focus:ring-primary w-4 h-4 cursor-pointer'
