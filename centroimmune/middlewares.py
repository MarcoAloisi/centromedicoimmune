import os
import base64

class CSPNonceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a random nonce for each request
        request.nonce = base64.b64encode(os.urandom(16)).decode('utf-8')

        # Call the next middleware or view
        response = self.get_response(request)

        # Set the Content-Security-Policy header with the nonce
        response['Content-Security-Policy'] = (
            f"script-src 'self' 'nonce-{request.nonce}'; "
            f"style-src 'self' 'nonce-{request.nonce}' https://fonts.googleapis.com; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"font-src 'self' https://fonts.gstatic.com data:; "
            f"img-src 'self' data:; "
            f"connect-src 'self'; "
            f"frame-src 'none'; "
            f"form-action 'self'; "
            f"frame-ancestors 'self';"
        )
        
        return response
