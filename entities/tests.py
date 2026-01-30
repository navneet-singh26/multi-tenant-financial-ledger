
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Entity, EntityMembership, EntitySettings, EntityAuditLog
from .schema_manager import SchemaManager
from decimal import Decimal

User = get_user_model()


class EntityModelTest(TestCase):
    """Test cases for Entity model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_entity(self):
        """Test creating an entity."""
        entity = Entity.objects.create(
            name='Test Company',
            entity_type='company',
            status='active',
            currency='USD',
            timezone='UTC'
        )
        
        self.assertEqual(entity.name, 'Test Company')
        self.assertEqual(entity.entity_type, 'company')
        self.assertEqual(entity.status, 'active')
        self.assertTrue(entity.is_active)
    
    def test_entity_str_representation(self):
        """Test string representation of entity."""
        entity = Entity.objects.create(
            name='Test Company',
            entity_type='company'
        )
        
        self.assertEqual(str(entity), 'Test Company')
    
    def test_entity_schema_name_generation(self):
        """Test schema name generation."""
        entity = Entity.objects.create(
            name='Test Company',
            entity_type='company'
        )
        
        self.assertTrue(entity.schema_name.startswith('entity_'))
        self.assertEqual(len(entity.schema_name), 43)  # entity_ + 36 char UUID


class EntityMembershipModelTest(TestCase):
    """Test cases for EntityMembership model."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            email='member@example.com',
            password='testpass123'
        )
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company'
        )
    
    def test_create_membership(self):
        """Test creating a membership."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.owner,
            role='owner',
            status='active'
        )
        
        self.assertEqual(membership.entity, self.entity)
        self.assertEqual(membership.user, self.owner)
        self.assertEqual(membership.role, 'owner')
        self.assertTrue(membership.can_manage_users)
    
    def test_owner_permissions(self):
        """Test that owner has all permissions."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.owner,
            role='owner',
            status='active'
        )
        
        self.assertTrue(membership.can_view_financials)
        self.assertTrue(membership.can_create_transactions)
        self.assertTrue(membership.can_approve_transactions)
        self.assertTrue(membership.can_manage_users)
        self.assertTrue(membership.can_manage_settings)
    
    def test_member_default_permissions(self):
        """Test default permissions for member role."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.member,
            role='member',
            status='active'
        )
        
        self.assertTrue(membership.can_view_financials)
        self.assertFalse(membership.can_manage_users)
        self.assertFalse(membership.can_manage_settings)
    
    def test_unique_user_per_entity(self):
        """Test that a user can only have one membership per entity."""
        EntityMembership.objects.create(
            entity=self.entity,
            user=self.owner,
            role='owner',
            status='active'
        )
        
        with self.assertRaises(Exception):
            EntityMembership.objects.create(
                entity=self.entity,
                user=self.owner,
                role='admin',
                status='active'
            )


class EntityAPITest(APITestCase):
    """Test cases for Entity API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company',
            status='active'
        )
        
        EntityMembership.objects.create(
            entity=self.entity,
            user=self.user,
            role='owner',
            status='active'
        )
    
    def test_list_entities(self):
        """Test listing entities."""
        response = self.client.get('/api/entities/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_entity(self):
        """Test creating an entity."""
        data = {
            'name': 'New Company',
            'entity_type': 'company',
            'currency': 'USD',
            'timezone': 'UTC'
        }
        
        response = self.client.post('/api/entities/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Company')
    
    def test_retrieve_entity(self):
        """Test retrieving a specific entity."""
        response = self.client.get(f'/api/entities/{self.entity.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Company')
    
    def test_update_entity(self):
        """Test updating an entity."""
        data = {
            'name': 'Updated Company Name'
        }
        
        response = self.client.patch(
            f'/api/entities/{self.entity.id}/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Company Name')
    
    def test_activate_entity(self):
        """Test activating an entity."""
        self.entity.status = 'inactive'
        self.entity.is_active = False
        self.entity.save()
        
        response = self.client.post(
            f'/api/entities/{self.entity.id}/activate/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.status, 'active')
        self.assertTrue(self.entity.is_active)
    
    def test_deactivate_entity(self):
        """Test deactivating an entity."""
        response = self.client.post(
            f'/api/entities/{self.entity.id}/deactivate/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.status, 'inactive')
        self.assertFalse(self.entity.is_active)
    
    def test_entity_statistics(self):
        """Test getting entity statistics."""
        response = self.client.get(
            f'/api/entities/{self.entity.id}/statistics/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_members', response.data)
        self.assertIn('active_members', response.data)
    
    def test_entity_audit_logs(self):
        """Test getting entity audit logs."""
        EntityAuditLog.objects.create(
            entity=self.entity,
            user=self.user,
            action='created',
            description='Entity created'
        )
        
        response = self.client.get(
            f'/api/entities/{self.entity.id}/audit_logs/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


class EntityMembershipAPITest(APITestCase):
    """Test cases for EntityMembership API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            email='member@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.owner)
        
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company'
        )
        
        self.owner_membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.owner,
            role='owner',
            status='active'
        )
    
    def test_invite_member(self):
        """Test inviting a member to entity."""
        data = {
            'entity_id': str(self.entity.id),
            'email': 'newmember@example.com',
            'role': 'member'
        }
        
        response = self.client.post('/api/memberships/invite/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_accept_invitation(self):
        """Test accepting an invitation."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.member,
            role='member',
            status='invited',
            invited_by=self.owner
        )
        
        self.client.force_authenticate(user=self.member)
        
        response = self.client.post(
            f'/api/memberships/{membership.id}/accept_invitation/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        membership.refresh_from_db()
        self.assertEqual(membership.status, 'active')
    
    def test_remove_member(self):
        """Test removing a member from entity."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.member,
            role='member',
            status='active'
        )
        
        response = self.client.post(
            f'/api/memberships/{membership.id}/remove/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            EntityMembership.objects.filter(id=membership.id).exists()
        )
    
    def test_cannot_remove_owner(self):
        """Test that owner cannot be removed."""
        response = self.client.post(
            f'/api/memberships/{self.owner_membership.id}/remove/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_member_role(self):
        """Test updating a member's role."""
        membership = EntityMembership.objects.create(
            entity=self.entity,
            user=self.member,
            role='member',
            status='active'
        )
        
        response = self.client.put(
            f'/api/memberships/{membership.id}/update_role/',
            data={'role': 'admin'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        membership.refresh_from_db()
        self.assertEqual(membership.role, 'admin')
    

    def test_cannot_update_owner_role(self):
        """Test that owner role cannot be changed."""
        data = {'role': 'admin'}
        
        response = self.client.patch(
            f'/api/memberships/{self.owner_membership.id}/update_role/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_memberships(self):
        """Test listing memberships."""
        response = self.client.get(
            f'/api/memberships/?entity_id={self.entity.id}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)


class SchemaManagerTest(TestCase):
    """Test cases for SchemaManager."""
    
    def setUp(self):
        """Set up test data."""
        self.entity = Entity.objects.create(
            name='Test Company',
            entity_type='company'
        )
        self.schema_manager = SchemaManager()
    
    def test_create_schema(self):
        """Test creating a schema for entity."""
        result = self.schema_manager.create_schema(self.entity.schema_name)
        self.assertTrue(result)
    
    def test_schema_exists(self):
        """Test checking if schema exists."""
        self.schema_manager.create_schema(self.entity.schema_name)
        exists = self.schema_manager.schema_exists(self.entity.schema_name)
        self.assertTrue(exists)
    
    def test_drop_schema(self):
        """Test dropping a schema."""
        self.schema_manager.create_schema(self.entity.schema_name)
        result = self.schema_manager.drop_schema(self.entity.schema_name)
        self.assertTrue(result)
        
        exists = self.schema_manager.schema_exists(self.entity.schema_name)
        self.assertFalse(exists)