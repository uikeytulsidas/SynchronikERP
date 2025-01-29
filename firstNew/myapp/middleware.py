import threading
import logging

logger = logging.getLogger(__name__)

# Thread-local storage to store the current user
_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = request.user
        logger.info(f"Current user set to: {request.user}")
        response = self.get_response(request)
        return response
