from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom Token Obtain Pair serializer for JWT token generation.
    It expects the user to login using email instead of username.
    """
    username = None  # Disable default username field, use email instead.

    email = serializers.EmailField()  # Email as the authentication field
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        User = get_user_model()

        # Ensure the user exists and authenticate using email and password
        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):
            # If the user is authenticated, return the token data
            data = super().validate(attrs)
            data['user'] = {
                "email": user.email,
                "full_name": user.full_name,
                "user_id": user.id,
            }
            return data
        else:
            raise serializers.ValidationError("Invalid credentials")