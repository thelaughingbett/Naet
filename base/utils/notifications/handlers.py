from django.conf import settings


class NotificationEngine:
    """Dispatches notifications across varoius communication channels."""

    @staticmethod
    def send_email(user, template_key="", context={}):
        # Implement email sending logic here
        pass

    @staticmethod
    def send_sms(user, template_key="", context={}):
        # implement sms sending logic here
        pass

    @classmethod
    def route(cls, user, template_key, channels, context):
        """Maps specific string keys to backend execution logic."""
        channel_mapping = {
            'email': cls.send_email,
            'sms': cls.send_sms,
        }

        for channel in channels:
            handler = channel_mapping.get(channel)
            if handler:
                handler(user, template_key, context)
