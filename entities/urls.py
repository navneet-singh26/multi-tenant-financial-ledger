
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EntityViewSet, EntityMembershipViewSet, EntitySettingsViewSet

router = DefaultRouter()
router.register(r'entities', EntityViewSet, basename='entity')
router.register(r'memberships', EntityMembershipViewSet, basename='membership')
router.register(r'settings', EntitySettingsViewSet, basename='settings')

urlpatterns = [
    path('', include(router.urls)),
]