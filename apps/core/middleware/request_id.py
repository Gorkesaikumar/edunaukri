import threading
import uuid

_thread_locals = threading.local()


def get_request_context():
    return {
        "request_id": getattr(_thread_locals, "request_id", "-"),
        "user_id": getattr(_thread_locals, "user_id", "-"),
        "ip_address": getattr(_thread_locals, "ip_address", "-"),
        "request_path": getattr(_thread_locals, "request_path", "-"),
        "status_code": getattr(_thread_locals, "status_code", "-"),
    }

def get_request_id():
    return getattr(_thread_locals, "request_id", None)


def set_request_context(**kwargs):
    for key, value in kwargs.items():
        setattr(_thread_locals, key, value)


def clear_request_context():
    for attr in ["request_id", "user_id", "ip_address", "request_path", "status_code"]:
        if hasattr(_thread_locals, attr):
            delattr(_thread_locals, attr)


class RequestIDMiddleware:
    """Inject or propagate X-Request-ID and contextual data for log correlation."""

    HEADER = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "-")

    def __call__(self, request):
        request_id = request.META.get(self.HEADER) or str(uuid.uuid4())
        
        # User might not be fully authenticated here if Auth middleware runs later,
        # but we capture what we can, and maybe update it in a custom view mixin or let the filter handle user dynamically.
        # It's better to dynamically get user_id from the request object attached to thread_locals if possible.
        # But wait, RequestIDMiddleware is high up in the stack. We'll store the `request` object itself!
        
        set_request_context(
            request_id=request_id,
            request_path=request.path,
            ip_address=self._get_client_ip(request),
        )
        # Store the request reference so filters can dynamically check user auth state which happens later in the middleware chain.
        _thread_locals.request = request
        
        request.request_id = request_id

        response = None
        try:
            response = self.get_response(request)
            set_request_context(status_code=response.status_code)
            response["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_context()
            if hasattr(_thread_locals, "request"):
                del _thread_locals.request
