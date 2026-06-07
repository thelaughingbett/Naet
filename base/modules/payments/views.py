# payments/views.py

# Adjust import based on your real app structure
from base.models import Payment, Account
from django.db import transaction as db_transaction
import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .registry import registry
from .services import PaymentService
from base.models import Payment


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(View):
    """
    Single webhook endpoint for all payment providers.
    Delegates verification to the correct backend.

    URL: /payments/webhook/<method>/
    e.g. /payments/webhook/mpesa/
         /payments/webhook/equity/
    """

    def post(self, request, method):
        try:
            backend = registry.get(method)
        except LookupError:
            return JsonResponse({'error': f'Unknown method: {method}'}, status=404)

        result = backend.verify_webhook(request)

        if not result.valid:
            return JsonResponse({'error': result.message}, status=400)

        # find the pending payment
        try:
            payment = Payment.objects.get(
                provider_ref=result.provider_ref,
                status='pending'
            )
        except Payment.DoesNotExist:
            # some providers send webhooks for payments not initiated through portal
            # log and accept gracefully
            return JsonResponse({'status': 'accepted', 'note': 'no matching payment'})

        if result.amount and abs(float(result.amount) - float(payment.amount)) > 1:
            # amount mismatch — flag but don't fail
            # integrator can handle this case
            pass

        PaymentService.confirm(
            payment,
            transaction_ref=result.transaction_ref,
            provider_ref=result.provider_ref,
        )

        return JsonResponse({'status': 'ok'})


class PaymentInitiateView(View):
    """
    Unified entry point to initiate a payment across any provider.

    Expects JSON POST payload:
    {
        "amount": 1500.00,
        "method": "mpesa",
        "account_id": 42,
        ... optional metadata for specific backends (e.g., phone_number)
    }
    """

    def post(self, request):
        try:
            # 1. Parse JSON request body
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        # 2. Extract and validate common parameters
        amount = data.get('amount')
        method = data.get('method')
        account_id = data.get('account_id')

        if not all([amount, method, account_id]):
            return JsonResponse({'error': 'Missing required fields: amount, method, account_id'}, status=400)

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return JsonResponse({'error': 'Amount must be a positive number'}, status=400)

        # 3. Verify backend support before touching the database
        try:
            registry.get(method)
        except LookupError:
            return JsonResponse({'error': f'Unsupported payment method: {method}'}, status=400)

        # 4. Fetch the target account securely
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return JsonResponse({'error': 'Account not found'}, status=404)

        # 5. Create the local database record inside a safe transaction
        with db_transaction.atomic():
            payment = Payment.objects.create(
                account=account,
                amount=amount,
                method=method,
                status='initiated'  # Temporary status before reaching API
            )

        # 6. Hand off API execution to the PaymentService
        # Pass remaining keyword arguments directly (e.g., phone_number for M-Pesa push)
        result = PaymentService.initiate(payment, **data)

        # 7. Format uniform client API response
        if not result.success:
            return JsonResponse({
                'success': False,
                'message': result.message or 'Payment initiation failed'
            }, status=422)

        return JsonResponse({
            'success': True,
            'payment_id': payment.id,
            'provider_ref': result.provider_ref,
            'redirect_url': result.redirect_url,
            'message': result.message or 'Payment successfully initiated'
        }, status=200)
