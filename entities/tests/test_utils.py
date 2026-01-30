
from django.test import TestCase
from django.contrib.auth import get_user_model
from entities.models import Entity, EntityMembership
from entities.utils import EntityHelper, EntityValidator
from django.core.exceptions import ValidationError

User = get_user_model()


class EntityHelperTestCase(TestCase):
    """Test cases for EntityHelper utility class."""
    
    def setUp(self):
        """Set up test data."""
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
            role='owner',
            status='active'
        )
    
    def test_generate_schema_name(self):
        """Test schema name generation."""
        schema_name = EntityHelper.generate_schema_name('Test Company')
        self.assertTrue(schema_name.startswith('entity_'))
        self.assertLessEqual(len(schema_name), 63)
    
    def test_get_user_entities(self):
        """Test getting user entities."""
        entities = EntityHelper.get_user_entities(self.user)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0], self.entity)
    
    def test_get_entity_members(self):
        """Test getting entity members."""
        members = EntityHelper.get_entity_members(self.entity)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0], self.user)
    
    def test_check_user_permission(self):
        """Test checking user permissions."""
        # Owner should have all permissions
        self.assertTrue(
            EntityHelper.check_user_permission(
                self.user,
                self.entity,
                'can_manage_settings'
            )
        )
    
    def test_bulk_invite_users(self):
        """Test bulk user invitation."""
        emails = ['user1@example.com', 'user2@example.com']
        results = EntityHelper.bulk_invite_users(
            self.entity,
            emails,
            'member',
            self.user
        )
        
        self.assertEqual(results['success'], 2)
        self.assertEqual(results['failed'], 0)


class EntityValidatorTestCase(TestCase):
    """Test cases for EntityValidator utility class."""
    
    def test_validate_entity_name(self):
        """Test entity name validation."""
        # Valid name
        EntityValidator.validate_entity_name('Test Company')
        
        # Too short
        with self.assertRaises(ValidationError):
            EntityValidator.validate_entity_name('A')
        
        # Too long
        with self.assertRaises(ValidationError):
            EntityValidator.validate_entity_name('A' * 256)
    
    def test_validate_currency_code(self):
        """Test currency code validation."""
        # Valid currency
        EntityValidator.validate_currency_code('USD')
        
        # Invalid currency
        with self.assertRaises(ValidationError):
            EntityValidator.validate_currency_code('INVALID')
    
    def test_validate_timezone(self):
        """Test timezone validation."""
        # Valid timezone
        EntityValidator.validate_timezone('UTC')
        EntityValidator.validate_timezone('America/New_York')
        
        # Invalid timezone
        with self.assertRaises(ValidationError):
            EntityValidator.validate_timezone('Invalid/Timezone')
    
    def test_validate_role(self):
        """Test role validation."""
        # Valid roles
        EntityValidator.validate_role('owner')
        EntityValidator.validate_role('admin')
        
        # Invalid role
        with self.assertRaises(ValidationError):
            EntityValidator.validate_role('invalid_role')
    
    def test_validate_entity_type(self):
        """Test entity type validation."""
        # Valid types
        EntityValidator.validate_entity_type('company')
        EntityValidator.validate_entity_type('individual')
        
        # Invalid type
        with self.assertRaises(ValidationError):
            EntityValidator.validate_entity_type('invalid_type')
    
    def test_validate_schema_name(self):
        """Test schema name validation."""
        # Valid schema names
        EntityValidator.validate_schema_name('entity_test123')
        EntityValidator.validate_schema_name('my_schema')
        
        # Invalid - starts with number
        with self.assertRaises(ValidationError):
            EntityValidator.validate_schema_name('123entity')
        
        # Invalid - uppercase
        with self.assertRaises(ValidationError):
            EntityValidator.validate_schema_name('Entity_Test')
        
        # Invalid - reserved name
        with self.assertRaises(ValidationError):
            EntityValidator.validate_schema_name('public')
        
        # Invalid - too long
        with self.assertRaises(ValidationError):
            EntityValidator.validate_schema_name('a' * 64)