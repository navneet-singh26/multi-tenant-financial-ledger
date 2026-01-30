
from django.contrib import admin
from .models import Entity, EntityMembership, EntitySettings, EntityAuditLog


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    """Admin interface for Entity model."""
    
    list_display = [
        'name', 'entity_type', 'status', 'is_active',
        'created_at', 'member_count'
    ]
    list_filter = ['entity_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'tax_id', 'registration_number']
    readonly_fields = ['created_at', 'updated_at', 'activated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'entity_type', 'status', 'is_active')
        }),
        ('Legal Information', {
            'fields': ('tax_id', 'registration_number', 'legal_name')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website', 'address')
        }),
        ('Settings', {
            'fields': ('currency', 'timezone', 'fiscal_year_start')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at', 'activated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        """Return count of active members."""
        return obj.memberships.filter(status='active').count()
    member_count.short_description = 'Members'


@admin.register(EntityMembership)
class EntityMembershipAdmin(admin.ModelAdmin):
    """Admin interface for EntityMembership model."""
    
    list_display = [
        'user', 'entity', 'role', 'status',
        'invited_by', 'created_at'
    ]
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['user__email', 'entity__name']
    readonly_fields = ['created_at', 'updated_at', 'invitation_accepted_at']
    
    fieldsets = (
        ('Membership Information', {
            'fields': ('entity', 'user', 'role', 'status')
        }),
        ('Permissions', {
            'fields': (
                'can_view_financials', 'can_create_transactions',
                'can_approve_transactions', 'can_manage_users',
                'can_manage_settings'
            )
        }),
        ('Invitation Details', {
            'fields': ('invited_by', 'invitation_accepted_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EntitySettings)
class EntitySettingsAdmin(admin.ModelAdmin):
    """Admin interface for EntitySettings model."""
    
    list_display = [
        'entity', 'default_payment_terms', 'require_approval',
        'enable_multi_currency', 'updated_at'
    ]
    list_filter = ['require_approval', 'enable_multi_currency', 'updated_at']
    search_fields = ['entity__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Entity', {
            'fields': ('entity',)
        }),
        ('Financial Settings', {
            'fields': (
                'default_payment_terms', 'default_payment_method',
                'enable_multi_currency', 'auto_reconcile'
            )
        }),
        ('Approval Settings', {
            'fields': ('require_approval', 'approval_threshold')
        }),
        ('Notification Settings', {
            'fields': (
                'notification_email', 'send_payment_reminders',
                'send_low_balance_alerts'
            )
        }),
        ('Custom Settings', {
            'fields': ('custom_settings',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EntityAuditLog)
class EntityAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for EntityAuditLog model."""
    
    list_display = [
        'entity', 'user', 'action', 'description',
        'ip_address', 'created_at'
    ]
    list_filter = ['action', 'created_at']
    search_fields = ['entity__name', 'user__email', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('entity', 'user', 'action', 'description')
        }),
        ('Changes', {
            'fields': ('changes',),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of audit logs."""
        return False