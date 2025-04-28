# /middleware.py

from django.shortcuts import HttpResponse
from django.urls import reverse

import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from .models import User

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip the middleware for non-API routes or if no Authorization header is found
        if not request.path.startswith('/api/') or 'Authorization' not in request.headers:
            return self.get_response(request)

        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Extract the token

            try:
                # Decode the JWT (this is where you verify the token)
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

                # Set the user from the token's payload
                user_id = payload.get('user_id')
                user = User.objects.get(id=user_id)

                # Attach the user to the request
                request.user = user

            except jwt.ExpiredSignatureError:
                raise AuthenticationFailed("Token has expired")
            except jwt.DecodeError:
                raise AuthenticationFailed("Invalid token")
            except User.DoesNotExist:
                raise AuthenticationFailed("User not found")

        return self.get_response(request)