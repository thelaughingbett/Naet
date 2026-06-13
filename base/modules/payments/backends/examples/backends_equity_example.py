

from base.modules.payments.backends import (
    AbstractPaymentBackend,
    PaymentInitiationResult,
    WebhookVerificationResult,
    PaymentFormConfig,

)


class EquityBankBackend(AbstractPaymentBackend):

    method = 'equity'

    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        # redirect student to Equity payment portal
        return PaymentInitiationResult(
            success=True,
            status='pending',
            redirect_url=f"https://equitypay.co.ke/pay?ref={payment.account.student.registration_number}&amount={payment.amount}",
            message='You will be redirected to Equity Bank payment portal'
        )

    def verify_webhook(self, request) -> WebhookVerificationResult:
        # verify Equity's signature and extract their fields
        pass

    def get_form_config(self) -> PaymentFormConfig:
        return PaymentFormConfig(
            method=self.method,
            label="Pay via Equity Bank",
            icon="🏦",
            flow="redirect",
            instructions="You will be redirected to your bank's payment portal.",
            fields=[
            ]
        )
