
import logging
import re
import uuid

from django.db.models import Q
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class EntityUtils:
    """Utility functions for entity operations."""
    
    @staticmethod
    def validate_tax_id(tax_id: str, country: str = 'US') -> bool:
        """
        Validate tax ID format based on country.
        
        Args:
            tax_id: Tax identification number
            country: Country code (default: US)
            
        Returns:
            bool: True if valid, False otherwise
        """
        if country == 'US':
            # US EIN format: XX-XXXXXXX
            import re
            pattern = r'^\d{2}-\d{7}$'
            return bool(re.match(pattern, tax_id))
        
        # Add more country validations as needed
        return True
    
    @staticmethod
    def format_address(address_dict: Dict) -> str:
        """
        Format address dictionary into a string.
        
        Args:
            address_dict: Dictionary containing address components
            
        Returns:
            str: Formatted address string
        """
        components = [
            address_dict.get('street'),
            address_dict.get('city'),
            address_dict.get('state'),
            address_dict.get('postal_code'),
            address_dict.get('country')
        ]
        
        return ', '.join(filter(None, components))
    
    @staticmethod
    def get_entity_statistics(entity) -> Dict:
        """
        Get comprehensive statistics for an entity.
        
        Args:
            entity: Entity instance
            
        Returns:
            dict: Statistics dictionary
        """
        from .models import EntityMembership
        
        memberships = entity.memberships.all()
        
        return {
            'total_members': memberships.count(),
            'active_members': memberships.filter(status='active').count(),
            'invited_members': memberships.filter(status='invited').count(),
            'suspended_members': memberships.filter(status='suspended').count(),
            'owners': memberships.filter(role='owner').count(),
            'admins': memberships.filter(role='admin').count(),
            'accountants': memberships.filter(role='accountant').count(),
            'members': memberships.filter(role='member').count(),
            'schema_name': entity.schema_name,
            'is_active': entity.is_active,
            'created_at': entity.created_at,
            'activated_at': entity.activated_at,
        }
    
    @staticmethod
    def check_entity_permission(user, entity, permission: str) -> bool:
        """
        Check if user has specific permission for entity.
        
        Args:
            user: User instance
            entity: Entity instance
            permission: Permission name
            
        Returns:
            bool: True if user has permission
        """
        try:
            membership = entity.memberships.get(
                user=user,
                status='active'
            )
            return getattr(membership, permission, False)
        except:
            return False
    
    @staticmethod
    def get_user_entities(user, status: Optional[str] = None) -> List:
        """
        Get all entities for a user.
        
        Args:
            user: User instance
            status: Optional status filter
            
        Returns:
            list: List of entities
        """
        from .models import Entity
        
        queryset = Entity.objects.filter(
            memberships__user=user,
            memberships__status='active'
        ).distinct()
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset)
    
    @staticmethod
    def transfer_ownership(entity, current_owner, new_owner) -> bool:
        """
        Transfer entity ownership to another user.
        
        Args:
            entity: Entity instance
            current_owner: Current owner user
            new_owner: New owner user
            
        Returns:
            bool: True if successful
        """
        from .models import EntityMembership
        
        try:
            # Get current owner membership
            current_membership = entity.memberships.get(
                user=current_owner,
                role='owner',
                status='active'
            )
            
            # Get or create new owner membership
            new_membership, created = entity.memberships.get_or_create(
                entity=entity,
                user=new_owner,
                defaults={
                    'role': 'owner',
                    'status': 'active'
                }
            )
            
            # Update roles
            new_membership.role = 'owner'
            new_membership.status = 'active'
            new_membership.save()
            
            current_membership.role = 'admin'
            current_membership.save()
            
            logger.info(
                f"Ownership transferred from {current_owner.email} to {new_owner.email} "
                f"for entity {entity.name}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to transfer ownership: {str(e)}")
            return False
    
    @staticmethod
    def bulk_invite_members(entity, inviter, email_list: List[str], role: str = 'member') -> Dict:
        """
        Invite multiple members to an entity.
        
        Args:
            entity: Entity instance
            inviter: User sending invitations
            email_list: List of email addresses
            role: Role to assign (default: member)
            
        Returns:
            dict: Results with success and failure counts
        """
        from django.contrib.auth import get_user_model
        from .models import EntityMembership
        
        User = get_user_model()
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for email in email_list:
            try:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={'username': email}
                )
                
                membership, created = EntityMembership.objects.get_or_create(
                    entity=entity,
                    user=user,
                    defaults={
                        'role': role,
                        'status': 'invited',
                        'invited_by': inviter
                    }
                )
                
                if created:
                    results['success'] += 1
                else:
                    results['errors'].append(f"{email}: Already a member")
                    results['failed'] += 1
                    
            except Exception as e:
                results['errors'].append(f"{email}: {str(e)}")
                results['failed'] += 1
        
        return results
    
    @staticmethod
    def export_entity_data(entity) -> Dict:
        """
        Export entity data for backup or migration.
        
        Args:
            entity: Entity instance
            
        Returns:
            dict: Complete entity data
        """
        from django.core.serializers import serialize
        import json
        
        data = {
            'entity': {
                'id': str(entity.id),
                'name': entity.name,
                'entity_type': entity.entity_type,
                'status': entity.status,
                'schema_name': entity.schema_name,
                'tax_id': entity.tax_id,
                'registration_number': entity.registration_number,
                'currency': entity.currency,
                'timezone': entity.timezone,
                'metadata': entity.metadata,
            },
            'memberships': [],
            'settings': None,
        }
        
        # Export memberships
        for membership in entity.memberships.all():
            data['memberships'].append({
                'user_email': membership.user.email,
                'role': membership.role,
                'status': membership.status,
                'permissions': {
                    'can_view_financials': membership.can_view_financials,
                    'can_create_transactions': membership.can_create_transactions,
                    'can_approve_transactions': membership.can_approve_transactions,
                    'can_manage_users': membership.can_manage_users,
                    'can_manage_settings': membership.can_manage_settings,
                }
            })
        
        # Export settings
        if hasattr(entity, 'settings'):
            data['settings'] = {
                'default_payment_terms': entity.settings.default_payment_terms,
                'require_approval': entity.settings.require_approval,
                'enable_multi_currency': entity.settings.enable_multi_currency,
                'custom_settings': entity.settings.custom_settings,
            }
        
        return data


class EntityHelper:
    """Helper class for entity-related operations."""
    
    @staticmethod
    def generate_schema_name(entity_name: str) -> str:
        """
        Generate a valid PostgreSQL schema name from entity name.
        
        Args:
            entity_name: The entity name
            
        Returns:
            Valid schema name
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        schema_name = re.sub(r'[^a-z0-9_]', '_', entity_name.lower())
        
        # Remove consecutive underscores
        schema_name = re.sub(r'_+', '_', schema_name)
        
        # Remove leading/trailing underscores
        schema_name = schema_name.strip('_')
        
        # Add prefix and unique suffix
        schema_name = f"entity_{schema_name}_{uuid.uuid4().hex[:8]}"
        
        # Ensure it's not too long (PostgreSQL limit is 63 chars)
        if len(schema_name) > 63:
            schema_name = schema_name[:55] + uuid.uuid4().hex[:8]
        
        return schema_name
    
    @staticmethod
    def get_user_entities(user, status: Optional[str] = 'active'):
        """
        Get all entities a user is a member of.
        
        Args:
            user: User instance
            status: Filter by membership status (default: 'active')
            
        Returns:
            QuerySet of Entity objects
        """
        from entities.models import Entity, EntityMembership
        
        query = Q(memberships__user=user)
        if status:
            query &= Q(memberships__status=status)
        
        return Entity.objects.filter(query).distinct()
    
    @staticmethod
    def get_user_role(user, entity) -> Optional[str]:
        """
        Get user's role in an entity.
        
        Args:
            user: User instance
            entity: Entity instance
            
        Returns:
            Role string or None
        """
        from entities.models import EntityMembership
        
        try:
            membership = EntityMembership.objects.get(
                user=user,
                entity=entity,
                status='active'
            )
            return membership.role
        except EntityMembership.DoesNotExist:
            return None
    
    @staticmethod
    def has_permission(user, entity, permission: str) -> bool:
        """
        Check if user has a specific permission in an entity.
        
        Args:
            user: User instance
            entity: Entity instance
            permission: Permission name (e.g., 'can_manage_settings')
            
        Returns:
            Boolean indicating if user has permission
        """
        from entities.models import EntityMembership
        
        try:
            membership = EntityMembership.objects.get(
                user=user,
                entity=entity,
                status='active'
            )
            return getattr(membership, permission, False)
        except EntityMembership.DoesNotExist:
            return False
    
    @staticmethod
    def get_entity_members(entity, status: Optional[str] = 'active'):
        """
        Get all members of an entity.
        
        Args:
            entity: Entity instance
            status: Filter by membership status (default: 'active')
            
        Returns:
            QuerySet of EntityMembership objects
        """
        from entities.models import EntityMembership
        
        query = Q(entity=entity)
        if status:
            query &= Q(status=status)
        
        return EntityMembership.objects.filter(query).select_related('user')
    
    @staticmethod
    def get_entity_stats(entity) -> dict:
        """
        Get statistics for an entity.
        
        Args:
            entity: Entity instance
            
        Returns:
            Dictionary with entity statistics
        """
        from entities.models import EntityMembership, EntityAuditLog
        
        return {
            'total_members': entity.memberships.filter(status='active').count(),
            'pending_invitations': entity.memberships.filter(status='invited').count(),
            'total_audit_logs': entity.audit_logs.count(),
            'created_at': entity.created_at,
            'last_updated': entity.updated_at,
        }


class EntityValidator:
    """Validator class for entity-related data."""
    
    @staticmethod
    def validate_entity_name(name: str) -> None:
        """
        Validate entity name.
        
        Args:
            name: Entity name to validate
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name or len(name.strip()) < 2:
            raise ValidationError('Entity name must be at least 2 characters long')
        
        if len(name) > 255:
            raise ValidationError('Entity name must not exceed 255 characters')
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9\s\-\.\,\&]+$', name):
            raise ValidationError(
                'Entity name can only contain letters, numbers, spaces, and basic punctuation'
            )
    
    @staticmethod
    def validate_tax_id(tax_id: str, country: str = 'US') -> None:
        """
        Validate tax ID format.
        
        Args:
            tax_id: Tax ID to validate
            country: Country code (default: 'US')
            
        Raises:
            ValidationError: If tax ID is invalid
        """
        if not tax_id:
            return
        
        # US EIN format: XX-XXXXXXX
        if country == 'US':
            if not re.match(r'^\d{2}-\d{7}$', tax_id):
                raise ValidationError(
                    'US Tax ID must be in format XX-XXXXXXX'
                )
    
    @staticmethod
    def validate_currency(currency: str) -> None:
        """
        Validate currency code.
        
        Args:
            currency: Currency code to validate
            
        Raises:
            ValidationError: If currency is invalid
        """
        valid_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'AUD', 'CAD',
            'CHF', 'SEK', 'NZD', 'MXN', 'SGD', 'HKD', 'NOK', 'KRW'
        ]
        
        if currency not in valid_currencies:
            raise ValidationError(
                f'Invalid currency code. Must be one of: {", ".join(valid_currencies)}'
            )
    
    @staticmethod
    def validate_timezone(timezone: str) -> None:
        """
        Validate timezone.
        
        Args:
            timezone: Timezone to validate
            
        Raises:
            ValidationError: If timezone is invalid
        """
        import pytz
        
        if timezone not in pytz.all_timezones:
            raise ValidationError(f'Invalid timezone: {timezone}')
    
    @staticmethod
    def validate_email(email: str) -> None:
        """
        Validate email address.
        
        Args:
            email: Email to validate
            
        Raises:
            ValidationError: If email is invalid
        """
        from django.core.validators import validate_email as django_validate_email
        
        try:
            django_validate_email(email)
        except ValidationError:
            raise ValidationError(f'Invalid email address: {email}')


class EntityPermissionChecker:
    """Helper class for checking entity permissions."""
    
    def __init__(self, user, entity):
        """
        Initialize permission checker.
        
        Args:
            user: User instance
            entity: Entity instance
        """
        self.user = user
        self.entity = entity
        self._membership = None
    
    @property
    def membership(self):
        """Get user's membership (cached)."""
        if self._membership is None:
            from entities.models import EntityMembership
            
            try:
                self._membership = EntityMembership.objects.get(
                    user=self.user,
                    entity=self.entity,
                    status='active'
                )
            except EntityMembership.DoesNotExist:
                pass
        
        return self._membership
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        if not self.membership:
            return False
        
        return getattr(self.membership, permission, False)
    
    def has_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        if not self.membership:
            return False
        
        return self.membership.role in roles
    
    def is_owner(self) -> bool:
        """Check if user is entity owner."""
        return self.has_role('owner')
    
    def is_admin(self) -> bool:
        """Check if user is admin or owner."""
        return self.has_role('owner', 'admin')
    
    def can_manage_settings(self) -> bool:
        """Check if user can manage entity settings."""
        return self.has_permission('can_manage_settings')
    
    def can_manage_members(self) -> bool:
        """Check if user can manage entity members."""
        return self.has_permission('can_manage_members')
    
    def can_create_transactions(self) -> bool:
        """Check if user can create transactions."""