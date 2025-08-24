import logging
import traceback
from django.http import HttpResponse

logger = logging.getLogger('interviews')

class ErrorLoggingMiddleware:
    """Middleware to log all errors and exceptions"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"[DEBUG] ErrorLoggingMiddleware: Processing request to {request.path}")
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """Log any unhandled exceptions"""
        print(f"[ERROR] ErrorLoggingMiddleware: Unhandled exception: {str(exception)}")
        print(f"[ERROR] ErrorLoggingMiddleware: Request path: {request.path}")
        print(f"[ERROR] ErrorLoggingMiddleware: Request method: {request.method}")
        print(f"[ERROR] ErrorLoggingMiddleware: Traceback: {traceback.format_exc()}")
        
        logger.error(f"Unhandled exception in {request.path}: {str(exception)}", exc_info=True)
        
        # Return a simple error response
        return HttpResponse("Internal server error", status=500)
