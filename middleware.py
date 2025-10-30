import logging
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

class AdminStatsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add CORS headers for /api/request-stats/
        if request.path.endswith('/api/request-stats/'):
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        return response

import logging
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

User = get_user_model()

import logging
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

User = get_user_model()

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Validate token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                
                # Fetch the full user from the database
                try:
                    user = User.objects.get(id=user_id)
                    request.user = user  # Attach the full user object
                    
                    # Debugging
                    print(f"Authenticated User: {user.username}, is_staff: {user.is_staff}, is_superuser: {user.is_superuser}")

                except User.DoesNotExist:
                    print("User not found")
                    return JsonResponse({'error': 'User not found'}, status=401)

            except (InvalidToken, TokenError) as e:
                print(f"Token validation error: {str(e)}")
                return JsonResponse({
                    'error': 'Invalid token',
                    'detail': str(e)
                }, status=401)

        response = self.get_response(request)
        return response
