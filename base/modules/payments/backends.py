from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentInitiationResult:
    """
    Returned by every backend after initiating a payment.
    The backend fills in what it knows — the rest is None.
    """
    success:      bool
    provider_ref: Optional[str] = None   # CheckoutRequestID, bank ref, etc.
    message:      str = ""               # user-facing message
    # for redirect-based flows (bank portals)
    redirect_url: Optional[str] = None
    raw_response: Optional[dict] = None  # full provider response for logging


@dataclass
class WebhookVerificationResult:
    """
    Returned after verifying an incoming webhook.
    """
    valid:           bool
    # final confirmed ref (MpesaReceiptNumber etc.)
    transaction_ref: Optional[str] = None
    provider_ref:    Optional[str] = None  # matches payment.provider_ref
    amount:          Optional[float] = None
    message:         str = ""
    raw_payload:     Optional[dict] = None


class AbstractPaymentBackend(ABC):
    """
    Contract every payment provider must implement.

    Integrators subclass this and implement the two abstract methods.
    Everything else — balance updates, notifications, audit trail —
    is handled by the core system.
    """

    # set this in your subclass
    method: str = ""  # must match Payment.PAYMENT_METHOD_CHOICES key

    @abstractmethod
    def initiate(
        self,
        payment,         # Payment instance
        **kwargs
    ) -> PaymentInitiationResult:
        """
        Start the payment process.

        What this means depends on the provider:
        - M-Pesa: send STK push, return CheckoutRequestID
        - Bank portal: return redirect_url to bank payment page
        - Cash: immediately return success (no async step)

        Do NOT update the Payment record here.
        Return a PaymentInitiationResult and let the core handle it.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        request,        # HttpRequest
    ) -> WebhookVerificationResult:
        """
        Parse and verify an incoming webhook from the provider.

        Verify the signature, extract the transaction reference,
        and return a WebhookVerificationResult.

        Return valid=False if the webhook is invalid or can't be verified.
        Do NOT update any records here — just parse and verify.
        """
        raise NotImplementedError

    def get_webhook_url_name(self) -> str:
        """
        Override to return a named URL for this backend's webhook endpoint.
        Default: 'payment-webhook-{method}'
        """
        return f'payment-webhook-{self.method}'
