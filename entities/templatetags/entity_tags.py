
from django import template
from django.utils.safestring import mark_safe
from entities.models import EntityMembership

register = template.Library()


@register.filter
def has_entity_permission(user, permission_entity):
    """
    Check if user has specific permission for entity.
    
    Usage: {% if user|has_entity_permission:"can_manage_settings,entity_id" %}
    """
    try:
        permission, entity_id = permission_entity.split(',')
        
        membership = EntityMembership.objects.filter(
            entity_id=entity_id,
            user=user,
            status='active'
        ).first()
        
        if not membership:
            return False
        
        return getattr(membership, permission.strip(), False)
    except:
        return False


@register.filter
def has_entity_role(user, role_entity):
    """
    Check if user has specific role in entity.
    
    Usage: {% if user|has_entity_role:"owner,entity_id" %}
    """
    try:
        role, entity_id = role_entity.split(',')
        
        membership = EntityMembership.objects.filter(
            entity_id=entity_id,
            user=user,
            role=role.strip(),
            status='active'
        ).first()
        
        return membership is not None
    except:
        return False


@register.simple_tag
def get_entity_membership(user, entity):
    """
    Get user's membership for entity.
    
    Usage: {% get_entity_membership user entity as membership %}
    """
    try:
        return EntityMembership.objects.get(
            entity=entity,
            user=user,
            status='active'
        )
    except EntityMembership.DoesNotExist:
        return None


@register.inclusion_tag('entities/entity_selector.html')
def entity_selector(user, current_entity=None):
    """
    Render entity selector dropdown.
    
    Usage: {% entity_selector user current_entity %}
    """
    memberships = EntityMembership.objects.filter(
        user=user,
        status='active'
    ).select_related('entity').order_by('entity__name')
    
    return {
        'entities': [m.entity for m in memberships],
        'current_entity': current_entity,
    }


@register.filter
def entity_role_badge(role):
    """
    Return HTML badge for entity role.
    
    Usage: {{ membership.role|entity_role_badge }}
    """
    badges = {
        'owner': '<span class="badge bg-danger">Owner</span>',
        'admin': '<span class="badge bg-primary">Admin</span>',
        'accountant': '<span class="badge bg-info">Accountant</span>',
        'member': '<span class="badge bg-secondary">Member</span>',
    }
    
    return mark_safe(badges.get(role, f'<span class="badge bg-light">{role}</span>'))


@register.filter
def entity_status_badge(status):
    """
    Return HTML badge for entity status.
    
    Usage: {{ entity.status|entity_status_badge }}
    """
    badges = {
        'active': '<span class="badge bg-success">Active</span>',
        'pending': '<span class="badge bg-warning">Pending</span>',
        'suspended': '<span class="badge bg-danger">Suspended</span>',
        'archived': '<span class="badge bg-secondary">Archived</span>',
    }
    
    return mark_safe(badges.get(status, f'<span class="badge bg-light">{status}</span>'))


@register.simple_tag
def entity_member_count(entity):
    """
    Get count of active members in entity.
    
    Usage: {% entity_member_count entity %}
    """
    return entity.memberships.filter(status='active').count()


@register.filter
def format_currency(amount, currency='USD'):
    """
    Format amount with currency symbol.
    
    Usage: {{ amount|format_currency:entity.currency }}
    """
    symbols = {
        'USD': ',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'INR': '₹',
    }
    
    symbol = symbols.get(currency, currency)
    
    try:
        formatted_amount = f"{float(amount):,.2f}"
        return f"{symbol}{formatted_amount}"
    except:
        return f"{symbol}{amount}"