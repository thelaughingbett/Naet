from django.template.loader import render_to_string
from django.conf import settings
from typing import Optional

NOTIFICATION_TEMPLATES = {
    'payment_confirmed': {
        'email': {
            'subject':  'Payment Confirmed — KES {amount}',
            'html':     'base/notifications/email/payment_confirmed.html',
            'text':     'base/notifications/email/payment_confirmed.txt',
        },
        'sms': 'Your payment of KES {amount} has been confirmed. Ref: {ref}. Balance: KES {balance}.',
    },
    'payment_failed': {
        'email': {
            'subject':  'Payment Failed',
            'html':     'base/notifications/email/payment_failed.html',
            'text':     'base/notifications/email/payment_failed.txt',
        },
        'sms': 'Your payment of KES {amount} failed. Please try again or contact finance.',
    },
    'results_published': {
        'email': {
            'subject':  'Your Results Are Available',
            'html':     'base/notifications/email/results_published.html',
            'text':     'base/notifications/email/results_published.txt',
        },
        'sms': 'Your {session} results are now available on the student portal.',
    },
    'reporting_confirmed': {
        'email': {
            'subject':  'Reporting Confirmed — {session}',
            'html':     'base/notifications/email/reporting_confirmed.html',
            'text':     'base/notifications/email/reporting_confirmed.txt',
        },
        'sms': 'Reporting for {session} confirmed. Welcome back, {student_name}.',
    },
    'fee_reminder': {
        'email': {
            'subject':  'Fee Payment Reminder — KES {balance} Due',
            'html':     'base/notifications/email/fee_reminder.html',
            'text':     'base/notifications/email/fee_reminder.txt',
        },
        'sms': 'Reminder: KES {balance} due by {due_date}. Pay now at the student portal.',
    },
    'enrollment_approved': {
        'email': {
            'subject':  'Unit Registration Approved',
            'html':     'base/notifications/email/enrollment_approved.html',
            'text':     'base/notifications/email/enrollment_approved.txt',
        },
        'sms': 'Your unit registration for {session} has been approved.',
    },
    'registration_success': {
        'email': {
            'subject':  'Registration Sucess',
            'html':     'base/notifications/email/registration_success.html',
            'text':     'base/notifications/email/registration_success.txt',
        },
        'sms': 'Welcome to instituion 🥳'
    }
}


def render_email(template_key: str, context: dict) -> tuple[str, str, str]:
    """
    Render email subject, HTML body, and plain-text body from a template key.
    Returns (subject, html_body, text_body).
    """
    template_config = NOTIFICATION_TEMPLATES.get(template_key, {}).get('email')
    if not template_config:
        raise ValueError(
            f"No email template registered for key '{template_key}'")

    subject = template_config['subject'].format(**context)
    html_body = render_to_string(template_config['html'], context)
    text_body = render_to_string(template_config['text'], context)

    return subject, html_body, text_body


def render_sms(template_key: str, context: dict) -> str:
    """
    Render SMS body from a template key.
    Returns the message string.
    """
    sms_template = NOTIFICATION_TEMPLATES.get(template_key, {}).get('sms')
    if not sms_template:
        raise ValueError(
            f"No SMS template registered for key '{template_key}'")

    return sms_template.format(**context)
