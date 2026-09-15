import json
import socket
import smtplib

from django.core.mail import EmailMessage, get_connection
from django.http import JsonResponse
from django.views import View

from base.models import Curriculum, Enrollment
from staffConsole.views.base import RoleRequiredMixin


def _friendly_email_error(exc: Exception) -> str:
    """
    Maps low-level connection/SMTP exceptions to a message an end user
    (a lecturer, not a developer) can actually act on, instead of a raw
    WinError/OSError string leaking a socket errno.
    """
    if isinstance(exc, (ConnectionRefusedError, socket.timeout)):
        return "Couldn't reach the mail server. Email sending isn't configured on this environment right now — try again later or contact IT support."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Mail server rejected the login credentials. Contact IT support."
    if isinstance(exc, smtplib.SMTPException):
        return "The mail server rejected the message. Please try again."
    if isinstance(exc, OSError):
        # Catches WinError 10061 and other platform-specific socket errors
        # that don't map to a more specific smtplib exception above.
        return "Couldn't reach the mail server. Email sending isn't configured on this environment right now — try again later or contact IT support."
    return "Something went wrong sending the email. Please try again."


class SendStudentEmailView(RoleRequiredMixin, View):
    required_role = 'lecturer'

    def post(self, request):

        lecturer = self.get_profile()
        try:
            data = json.loads(request.body)
            to = data['to'].strip()
            subject = data['subject'].strip()
            message = data['message'].strip()

        except (KeyError, json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        if not to or not subject or not message:
            return JsonResponse({'error': 'To, subject, and message are required.'}, status=400)

        is_valid_recipient = Enrollment.objects.filter(
            curriculum__professor=lecturer,
            status='approved',
            student__school_email__iexact=to,
        ).exists()

        if not is_valid_recipient:
            return JsonResponse({'error': 'That address is not a school email for one of your enrolled students.'}, status=400)

        from_email = lecturer.school_email

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[to],
            reply_to=[from_email],
        )
        try:
            email.send(fail_silently=False)
        except Exception as e:
            return JsonResponse({'error': _friendly_email_error(e)}, status=502)

        return JsonResponse({'success': True})


class SendBulkEmailView(RoleRequiredMixin, View):
    required_role = 'lecturer'

    def post(self, request):

        lecturer = self.get_profile()

        try:
            data = json.loads(request.body)
            curriculum_id = data['curriculum_id']
            recipients = data['recipients']
            subject = data['subject'].strip()
            message = data['message'].strip()

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Bad payload'}, status=400)

        if not subject or not message:
            return JsonResponse({'error': 'Subject and message are required.'}, status=400)

        if not recipients:
            return JsonResponse({'error': 'No recipients provided.'}, status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id,
                professor=lecturer
            )

        except Curriculum.DoesNotExist:
            return JsonResponse({'error': 'Course not found.'}, status=404)

        valid_emails = {
            e.lower() for e in
            Enrollment.objects.filter(
                curriculum=curriculum,
                status='approved'
            )
            .select_related('student')
            .values_list('student__school_email', flat=True)
            if e
        }

        from_email = lecturer.school_email

        try:
            connection = get_connection()
            connection.open()
        except Exception as e:
            return JsonResponse({'error': _friendly_email_error(e)}, status=502)

        messages = []
        skipped = []

        for r in recipients:
            addr = (r.get('email') or '').strip()
            name = r.get('name', '')
            if addr.lower() not in valid_emails:
                skipped.append(addr)
                continue

            body = message.replace(
                '{{name}}',
                name
            ) if '{{name}}' in message else message

            messages.append(
                EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=from_email,
                    to=[addr],
                    reply_to=[from_email],
                    connection=connection,
                )
            )

        if not messages:
            connection.close()
            return JsonResponse({'error': "None of the submitted recipients matched an enrolled student's school email."}, status=400)

        try:
            sent_count = connection.send_messages(messages)
        except Exception as e:
            return JsonResponse({'error': _friendly_email_error(e)}, status=502)
        finally:
            connection.close()

        return JsonResponse({'sent': sent_count or len(messages), 'errors': skipped})
