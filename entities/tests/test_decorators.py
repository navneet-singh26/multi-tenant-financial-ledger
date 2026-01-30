
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from entities.models import Entity, EntityMembership
from entities.decorators import (
    require_entity_permission,
    require_entity_role,
    require_active_entity,
    entity_context_required
)

User = get_user_model()


class DecoratorTestCase(TestCase):
    """Test cases for entity decorators."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            
            password='testpass123'
        )
        
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company',
            currency='USD',
            timezone='UTC',
            status='active',
            is_active=True
        )
        
        self.membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.user,
            role='admin',
            status='active'
        )
    
    def test_require_entity_permission_success(self):
        """Test decorator with valid permission."""
        @require_entity_permission('can_view_reports')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_require_entity_permission_denied(self):
        """Test decorator with missing permission."""
        # Set permission to False
        self.membership.can_view_reports = False
        self.membership.save()
        
        @require_entity_permission('can_view_reports')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 403)
    
    def test_require_entity_permission_no_auth(self):
        """Test decorator without authentication."""
        from django.contrib.auth.models import AnonymousUser
        
        @require_entity_permission('can_view_reports')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = AnonymousUser()
        
        response = test_view(request)
        self.assertEqual(response.status_code, 401)
    
    def test_require_entity_role_success(self):
        """Test role decorator with valid role."""
        @require_entity_role('admin', 'owner')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_require_entity_role_denied(self):
        """Test role decorator with invalid role."""
        @require_entity_role('owner')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 403)
    
    def test_require_active_entity_success(self):
        """Test active entity decorator with active entity."""
        @require_active_entity
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_require_active_entity_inactive(self):
        """Test active entity decorator with inactive entity."""
        self.entity.is_active = False
        self.entity.save()
        
        @require_active_entity
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 403)
    
    def test_entity_context_required_success(self):
        """Test context required decorator with context."""
        @entity_context_required
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get('/')
        request.user = self.user
        request.entity = self.entity
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_entity_context_required_missing(self):
        """Test context required decorator without context."""
        @entity_context_required
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = self.factory.get('/')
        request.user = self.user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 400)