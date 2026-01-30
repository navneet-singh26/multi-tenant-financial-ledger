

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, UserActivity


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""
    
    list_display = [
        'email', 'username', 'first_name', 'last_name',
        'is_active', 'is_verified', 'is_staff', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_verified', 'is_staff', 'is_superuser',
        'created_at', 'last_login'
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone_number']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'phone_number', 'avatar', 'bio', 'date_of_birth')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_verified', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'email_verified_at', 'date_joined')
        }),
        (_('Metadata'), {
            'fields': ('metadata', 'last_login_ip'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'first_name', 'last_name', 'is_active', 'is_staff'
            ),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('profile')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""
    
    list_display = [
        'user', 'job_title', 'department', 'employee_id',
        'city', 'country', 'created_at'
    ]
    list_filter = ['department', 'country', 'created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'job_title', 'department', 'employee_id', 'city'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Professional Information'), {
            'fields': ('job_title', 'department', 'employee_id')
        }),
        (_('Contact Information'), {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state', 'country', 'postal_code'
            )
        }),
        (_('Emergency Contact'), {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            ),
            'classes': ('collapse',)
        }),
        (_('Preferences'), {
            'fields': ('timezone', 'language', 'notification_preferences'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin configuration for UserActivity model."""
    
    list_display = [
        'user', 'action', 'ip_address', 'created_at'
    ]
    list_filter = ['action', 'created_at']
    search_fields = [
        'user__email', 'user__username', 'action',
        'description', 'ip_address'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Activity Information'), {
            'fields': ('user', 'action', 'description')
        }),
        (_('Request Details'), {
            'fields': ('ip_address', 'user_agent')
        }),
        (_('Metadata'), {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        (_('Timestamp'), {
            'fields': ('created_at',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """Disable manual creation of activities."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of activities."""
        return False