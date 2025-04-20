from django.urls import path
from .views import RegisterUserView, LoginView, ProfileView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("register/", RegisterUserView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    # Token refresh endpoint
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]