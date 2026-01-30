
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from entities.models import Entity, EntityMembership
from entities.middleware import (
    EntityContextMiddleware,
    EntityPermissionMiddleware
)

User = get_user_model()


class EntityContextMiddlewareTestCase(TestCase):
    """Test cases for EntityContextMiddleware."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = EntityContextMiddleware(get_response=lambda r: HttpResponse())
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company',
            currency='USD',
            timezone='UTC'
        )
        
        self.membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.user,
            role='admin',
            status='active'
        )
    
    def test_process_request_with_header(self):
        """Test processing request with entity ID in header."""
        request = self.factory.get('/')
        request.user = self.user
        request.META['HTTP_X_ENTITY_ID'] = str(self.entity.id)
        
        self.middleware.process_request(request)
        
        self.assertEqual(request.entity, self.entity)
        self.assertEqual(request.entity_membership, self.membership)
    
    def test_process_request_with_query_param(self):
        """Test processing request with entity ID in query parameter."""
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = self.user
        
        self.middleware.process_request(request)
        
        self.assertEqual(request.entity, self.entity)
        self.assertEqual(request.entity_membership, self.membership)
    
    def test_process_request_no_entity_id(self):
        """Test processing request without entity ID."""
        request = self.factory.get('/')
        request.user = self.user
        
        self.middleware.process_request(request)
        
        self.assertIsNone(request.entity)
    
    def test_process_request_unauthenticated(self):
        """Test processing request for unauthenticated user."""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        self.middleware.process_request(request)
        
        self.assertIsNone(request.entity)
    
    def test_process_request_invalid_entity(self):
        """Test processing request with invalid entity ID."""
        request = self.factory.get('/?entity_id=99999')
        request.user = self.user
        
        self.middleware.process_request(request)
        
        self.assertIsNone(request.entity)
    
    def test_process_request_no_membership(self):
        """Test processing request when user is not a member."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        request = self.factory.get(f'/?entity_id={self.entity.id}')
        request.user = other_user
        
        self.middleware.process_request(request)
        
        self.assertIsNone(request.entity)
    
    def test_process_response_adds_headers(self):
        """Test that response includes entity headers."""
        request = self.factory.get('/')
        request.user = self.user
        request.entity = self.entity
        
        response = HttpResponse()
        response = self.middleware.process_response(request, response)
        
        self.assertEqual(response['X-Entity-ID'], str(self.entity.id))
        self.assertEqual(response['X-Entity-Name'], self.entity.name)