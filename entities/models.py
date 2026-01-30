from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import uuid


class Entity(models.Model):
    """
    Represents a business entity (company/organization) in the multi-tenant system.
    Each entity gets its own PostgreSQL schema for data isolation.
    """
    ENTITY_TYPE_CHOICES = [
        ('company', 'Company'),
        ('partnership', 'Partnership'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('nonprofit', 'Non-Profit Organization'),
        ('government', 'Government Entity'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=255, unique=True)
    legal_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES)
    
    # Registration Details
    registration_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    tax_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # Schema Information
    schema_name = models.CharField(
        max_length=63,  # PostgreSQL schema name limit
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z][a-z0-9_]*$',
                message='Schema name must start with a letter and contain only lowercase letters, numbers, and underscores.'
            )
        ]
    )
    
    # Contact Information
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    
    # Financial Settings
    base_currency = models.CharField(max_length=3, default='USD')
    fiscal_year_start = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    
    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_entities'
    )
    
    # Metadata
    settings_json = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'entities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['schema_name']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['entity_type']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')
    
    def __str__(self):
        return f"{self.name} ({self.schema_name})"
    
    def save(self, *args, **kwargs):
        """Override save to generate schema name if not provided."""
        if not self.schema_name:
            # Generate schema name from entity name
            base_name = self.name.lower().replace(' ', '_')
            base_name = ''.join(c for c in base_name if c.isalnum() or c == '_')
            self.schema_name = f"entity_{base_name}"[:63]
        
        super().save(*args, **kwargs)


class EntityMembership(models.Model):
    """
    Represents a user's membership in an entity with specific roles.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('accountant', 'Accountant'),
        ('auditor', 'Auditor'),
        ('viewer', 'Viewer'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('invited', 'Invited'),
        ('suspended', 'Suspended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entity_memberships')
    
    # Role and Status
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    
    # Permissions
    can_manage_users = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    can_create_entries = models.BooleanField(default=False)
    can_approve_entries = models.BooleanField(default=False)
    
    # Invitation
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invitation_token = models.CharField(max_length=100, blank=True, null=True, unique=True)
    invitation_sent_at = models.DateTimeField(blank=True, null=True)
    invitation_accepted_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'entity_memberships'
        unique_together = [['entity', 'user']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity', 'user']),
            models.Index(fields=['role', 'status']),
            models.Index(fields=['invitation_token']),
        ]
        verbose_name = _('Entity Membership')
        verbose_name_plural = _('Entity Memberships')
    
    def __str__(self):
        return f"{self.user.email} - {self.entity.name} ({self.role})"


class EntitySettings(models.Model):
    """
    Stores entity-specific configuration settings.
    """
    entity = models.OneToOneField(Entity, on_delete=models.CASCADE, related_name='entity_settings')
    
    # Accounting Settings
    chart_of_accounts_template = models.CharField(max_length=50, default='standard')
    enable_multi_currency = models.BooleanField(default=False)
    default_payment_terms = models.IntegerField(default=30)  # days
    
    # Approval Workflow
    require_approval_for_entries = models.BooleanField(default=True)
    approval_threshold_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Notification Settings
    email_notifications_enabled = models.BooleanField(default=True)
    notification_emails = models.JSONField(default=list, blank=True)
    
    # Integration Settings
    enable_payment_gateway = models.BooleanField(default=False)
    payment_gateway_config = models.JSONField(default=dict, blank=True)
    
    enable_erp_integration = models.BooleanField(default=False)
    erp_integration_config = models.JSONField(default=dict, blank=True)
    
    # Reporting Settings
    enable_consolidated_reporting = models.BooleanField(default=False)
    reporting_frequency = models.CharField(max_length=20, default='monthly')
    
    # Security Settings
    enable_two_factor_auth = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=60)
    password_expiry_days = models.IntegerField(default=90)
    
    # Custom Settings
    custom_settings = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'entity_settings'
        verbose_name = _('Entity Settings')
        verbose_name_plural = _('Entity Settings')
    
    def __str__(self):
        return f"Settings for {self.entity.name}"


class EntityAuditLog(models.Model):
    """
    Audit log for entity-level changes.
    """
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('activated', 'Activated'),
        ('deactivated', 'Deactivated'),
        ('suspended', 'Suspended'),
        ('settings_changed', 'Settings Changed'),
        ('member_added', 'Member Added'),
        ('member_removed', 'Member Removed'),
        ('member_role_changed', 'Member Role Changed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entity_audit_logs'
    )
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    changes = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'entity_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
        verbose_name = _('Entity Audit Log')
        verbose_name_plural = _('Entity Audit Logs')
    
    def __str__(self):
        return f"{self.entity.name} - {self.action} at {self.created_at}"
3.2