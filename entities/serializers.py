
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Entity, EntityMembership, EntitySettings, EntityAuditLog
from .schema_manager import SchemaManager
import secrets

User = get_user_model()


class EntitySerializer(serializers.ModelSerializer):
    """Serializer for Entity model."""
    
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Entity
        fields = [
            'id', 'name', 'legal_name', 'entity_type', 'registration_number',
            'tax_id', 'schema_name', 'email', 'phone', 'website',
            'address_line1', 'address_line2', 'city', 'state', 'country',
            'postal_code', 'base_currency', 'fiscal_year_start', 'status',
            'is_active', 'created_by', 'created_by_email', 'member_count',
            'settings_json', 'metadata', 'created_at', 'updated_at', 'activated_at'
        ]
        read_only_fields = ['id', 'schema_name', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        """Get the number of active members."""
        return obj.memberships.filter(status='active').count()
    
    def create(self, validated_data):
        """Create entity and its schema."""
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        
        # Create the entity
        entity = super().create(validated_data)
        
        # Create PostgreSQL schema
        SchemaManager.create_schema(entity.schema_name)
        
        # Create entity settings
        EntitySettings.objects.create(entity=entity)
        
        # Add creator as owner
        EntityMembership.objects.create(
            entity=entity,
            user=self.context['request'].user,
            role='owner',
            status='active',
            can_manage_users=True,
            can_manage_settings=True,
            can_view_reports=True,
            can_create_entries=True,
            can_approve_entries=True
        )
        
        return entity


class EntityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for entity lists."""
    
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Entity
        fields = [
            'id', 'name', 'entity_type', 'status', 'is_active',
            'member_count', 'user_role', 'created_at'
        ]
    
    def get_member_count(self, obj):
        """Get the number of active members."""
        return obj.memberships.filter(status='active').count()
    
    def get_user_role(self, obj):
        """Get current user's role in this entity."""
        user = self.context['request'].user
        membership = obj.memberships.filter(user=user, status='active').first()
        return membership.role if membership else None


class EntityMembershipSerializer(serializers.ModelSerializer):
    """Serializer for EntityMembership model."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    
    class Meta:
        model = EntityMembership
        fields = [
            'id', 'entity', 'entity_name', 'user', 'user_email', 'user_name',
            'role', 'status', 'can_manage_users', 'can_manage_settings',
            'can_view_reports', 'can_create_entries', 'can_approve_entries',
            'invited_by', 'invited_by_email', 'invitation_token',
            'invitation_sent_at', 'invitation_accepted_at', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'invitation_token', 'invitation_sent_at',
            'invitation_accepted_at', 'created_at', 'updated_at'
        ]


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting members to an entity."""
    
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=EntityMembership.ROLE_CHOICES)
    can_manage_users = serializers.BooleanField(default=False)
    can_manage_settings = serializers.BooleanField(default=False)
    can_view_reports = serializers.BooleanField(default=True)
    can_create_entries = serializers.BooleanField(default=False)
    can_approve_entries = serializers.BooleanField(default=False)
    
    def validate_email(self, value):
        """Validate that user exists."""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value
    
    def create(self, validated_data):
        """Create membership invitation."""
        entity = self.context['entity']
        user = User.objects.get(email=validated_data['email'])
        invited_by = self.context['request'].user
        
        # Check if membership already exists
        membership, created = EntityMembership.objects.get_or_create(
            entity=entity,
            user=user,
            defaults={
                'role': validated_data['role'],
                'status': 'invited',
                'can_manage_users': validated_data['can_manage_users'],
                'can_manage_settings': validated_data['can_manage_settings'],
                'can_view_reports': validated_data['can_view_reports'],
                'can_create_entries': validated_data['can_create_entries'],
                'can_approve_entries': validated_data['can_approve_entries'],
                'invited_by': invited_by,
                'invitation_token': secrets.token_urlsafe(32),
                'invitation_sent_at': timezone.now()
            }
        )
        
        if not created:
            raise serializers.ValidationError("User is already a member of this entity.")
        
        return membership


class EntitySettingsSerializer(serializers.ModelSerializer):
    """Serializer for EntitySettings model."""
    
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    
    class Meta:
        model = EntitySettings
        fields = [
            'entity', 'entity_name', 'chart_of_accounts_template',
            'enable_multi_currency', 'default_payment_terms',
            'require_approval_for_entries', 'approval_threshold_amount',
            'email_notifications_enabled', 'notification_emails',
            'enable_payment_gateway', 'payment_gateway_config',
            'enable_erp_integration', 'erp_integration_config',
            'enable_consolidated_reporting', 'reporting_frequency',
            'enable_two_factor_auth', 'session_timeout_minutes',
            'password_expiry_days', 'custom_settings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['entity', 'created_at', 'updated_at']


class EntityAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for EntityAuditLog model."""
    
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EntityAuditLog
        fields = [
            'id', 'entity', 'entity_name', 'user', 'user_email',
            'action', 'description', 'changes', 'ip_address',
            'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EntityStatisticsSerializer(serializers.Serializer):
    """Serializer for entity statistics."""
    
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    pending_invitations = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    last_activity = serializers.DateTimeField()