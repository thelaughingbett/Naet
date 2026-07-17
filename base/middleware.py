import threading

# Thread-local storage to pass request parameters safely down into Django database save loops
_thread_locals = threading.local()


def get_current_request_context():
    """Extracts network identifiers safely from active execution threads."""
    return getattr(_thread_locals, 'request_info', None)


class SecurityAuditContextMiddleware:
    """
    Intercepts network variables (IP, User-Agent, Session User) and binds them 
    temporarily to the active thread for down-stream database signal processing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Parse client IP address accurately handling proxies/firewalls
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

        # 2. Extract context payloads
        _thread_locals.request_info = {
            'user': request.user if request.user.is_authenticated else None,
            'ip_address': ip,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown-Agent')
        }

        response = self.get_response(request)

        # 3. Wipe thread footprint cleanly post-execution cycle to avoid leakage
        if hasattr(_thread_locals, 'request_info'):
            del _thread_locals.request_info

        return response
