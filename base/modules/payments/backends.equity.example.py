

from base.modules.payments.backends import AbstractPaymentBackend, PaymentInitiationResult, WebhookVerificationResult


class EquityBankBackend(AbstractPaymentBackend):

    method = 'equity'

    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        # redirect student to Equity payment portal
        return PaymentInitiationResult(
            success=True,
            redirect_url=f"https://equitypay.co.ke/pay?ref={payment.account.student.registration_number}&amount={payment.amount}",
            message='You will be redirected to Equity Bank'
        )

    def verify_webhook(self, request) -> WebhookVerificationResult:
        # verify Equity's signature and extract their fields

        ...
