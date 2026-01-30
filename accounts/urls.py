
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, UserProfileDetailView, PasswordChangeView,
    UserActivityViewSet, UserListView, UserDetailView
)

app_name = 'accounts'

# Router for viewsets
router = DefaultRouter()
router.register(r'activities', UserActivityViewSet, basename='activity')

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile endpoints
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/details/', UserProfileDetailView.as_view(), name='profile-details'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    
    # User management (admin)
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:id>/', UserDetailView.as_view(), name='user-detail'),

    # Include router URLs
    path('', include(router.urls)),
]