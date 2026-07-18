import abc
from apps.guarantee_claims.models.refund import GuaranteeRefund

class RefundProvider(abc.ABC):
    """
    Abstract base class for refund providers (Manual, Razorpay, Stripe).
    Keeps payment gateway logic decoupled from the claim module.
    """
    
    @abc.abstractmethod
    def create_refund(self, refund: GuaranteeRefund, amount: float, method: str, transaction_ref: str = None, notes: str = None) -> bool:
        """Initiates the refund with the provider."""
        pass
        
    @abc.abstractmethod
    def get_refund_status(self, refund: GuaranteeRefund) -> str:
        """Gets current status from provider."""
        pass
        
    @abc.abstractmethod
    def verify_refund(self, refund: GuaranteeRefund) -> bool:
        """Verifies if a webhook/event actually matches our records."""
        pass
