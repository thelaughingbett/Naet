# payments/backends/mpesa.py

import requests
import base64
import json
import hmac
import hashlib
from datetime import datetime
from django.conf import settings
from base.modules.payments.backends import (
    AbstractPaymentBackend,
    PaymentInitiationResult,
    WebhookVerificationResult,
    PaymentFormConfig,
    FormField
)


class MpesaBackend(AbstractPaymentBackend):

    method = 'mpesa'

    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        phone = kwargs.get('phone_number') or payment.phone_number
        token = self._get_token()
        if not token:
            return PaymentInitiationResult(success=False, message='M-Pesa unavailable')

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
        ).decode()

        response = requests.post(
            'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
            json={
                "BusinessShortCode": settings.MPESA_SHORTCODE,
                "Password":          password,
                "Timestamp":         timestamp,
                "TransactionType":   "CustomerPayBillOnline",
                "Amount":            int(payment.amount),
                "PartyA":            phone,
                "PartyB":            settings.MPESA_SHORTCODE,
                "PhoneNumber":       phone,
                "CallBackURL":       settings.MPESA_CALLBACK_URL,
                "AccountReference":  payment.account.student.registration_number,
                "TransactionDesc":   "Fee payment",
            },
            headers={'Authorization': f'Bearer {token}'}
        ).json()

        if response.get('ResponseCode') == '0':
            return PaymentInitiationResult(
                status='completed',
                success=True,
                provider_ref=response.get('CheckoutRequestID'),
                message='Check your phone to complete payment',
                raw_response=response
            )
        return PaymentInitiationResult(
            success=False,
            status='failed',
            message=response.get('errorMessage', 'STK push failed'),
            raw_response=response
        )

    def verify_webhook(self, request) -> WebhookVerificationResult:
        try:
            body = json.loads(request.body)
            callback = body.get('Body', {}).get('stkCallback', {})
            code = callback.get('ResultCode')
            ref = callback.get('CheckoutRequestID')
        except Exception:
            return WebhookVerificationResult(valid=False, message='Invalid payload')

        if code != 0:
            return WebhookVerificationResult(
                valid=False,
                provider_ref=ref,
                message=callback.get('ResultDesc', 'Payment failed')
            )

        items = {
            item['Name']: item.get('Value')
            for item in callback.get('CallbackMetadata', {}).get('Item', [])
        }

        return WebhookVerificationResult(
            valid=True,
            transaction_ref=items.get('MpesaReceiptNumber'),
            provider_ref=ref,
            amount=items.get('Amount'),
            raw_payload=body
        )

    def _get_token(self):
        try:
            r = requests.get(
                'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials',
                auth=(settings.MPESA_CONSUMER_KEY,
                      settings.MPESA_CONSUMER_SECRET)
            )
            return r.json().get('access_token')
        except Exception:
            return None

    def get_form_config(self) -> PaymentFormConfig:
        return PaymentFormConfig(
            method="mpesa",
            label="Pay via M-Pesa",
            icon="📱",
            flow="stk_push",
            instructions="Enter your Safaricom number. You will receive a prompt on your phone.",
            fields=[
                FormField(
                    name="phone_number",
                    label="M-Pesa Phone Number",
                    type="tel",
                    placeholder="07XXXXXXXX",
                    help_text="Must be a registered Safaricom number"
                ),
            ]
        )
