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
        
        # Add the CSP header with the generated nonce
        response['Content-Security-Policy'] = f"script-src 'self' 'nonce-{request.nonce}' 'strict-dynamic'"
        
        return response
