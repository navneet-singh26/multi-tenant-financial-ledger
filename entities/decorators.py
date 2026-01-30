
from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from .models import Entity, EntityMembership


def require_entity_permission(permission):
    """
    Decorator to require specific entity permission.
    
    Usage:
        @require_entity_permission('can_manage_settings')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=401
                )
            
            # Get entity from request
            entity_id = kwargs.get('entity_id') or request.GET.get('entity_id')
            
            if not entity_id:
                return JsonResponse(
                    {'error': 'Entity ID required'},
                    status=400
                )
            
            try:
                entity = Entity.objects.get(id=entity_id)
            except Entity.DoesNotExist:
                return JsonResponse(
                    {'error': 'Entity not found'},
                    status=404
                )
            
            # Check membership and permission
            try:
                membership = EntityMembership.objects.get(
                    entity=entity,
                    user=request.user,
                    status='active'
                )
                
                if not getattr(membership, permission, False):
                    return JsonResponse(
                        {'error': f'Permission denied: {permission}'},
                        status=403
                    )
                
                # Add entity and membership to request
                request.entity = entity
                request.entity_membership = membership
                
            except EntityMembership.DoesNotExist:
                return JsonResponse(
                    {'error': 'Not a member of this entity'},
                    status=403
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_entity_role(*roles):
    """
    Decorator to require specific entity role(s).
    
    Usage:
        @require_entity_role('owner', 'admin')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=401
                )
            
            # Get entity from request
            entity_id = kwargs.get('entity_id') or request.GET.get('entity_id')
            
            if not entity_id:
                return JsonResponse(
                    {'error': 'Entity ID required'},
                    status=400
                )
            
            try:
                entity = Entity.objects.get(id=entity_id)
            except Entity.DoesNotExist:
                return JsonResponse(
                    {'error': 'Entity not found'},
                    status=404
                )
            
            # Check membership and role
            try:
                membership = EntityMembership.objects.get(
                    entity=entity,
                    user=request.user,
                    status='active'
                )
                
                if membership.role not in roles:
                    return JsonResponse(
                        {'error': f'Role required: {", ".join(roles)}'},
                        status=403
                    )
                
                # Add entity and membership to request
                request.entity = entity
                request.entity_membership = membership
                
            except EntityMembership.DoesNotExist:
                return JsonResponse(
                    {'error': 'Not a member of this entity'},
                    status=403
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_active_entity(view_func):
    """
    Decorator to require entity to be active.
    
    Usage:
        @require_active_entity
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get entity from request
        entity_id = kwargs.get('entity_id') or request.GET.get('entity_id')
        
        if not entity_id:
            return JsonResponse(
                {'error': 'Entity ID required'},
                status=400
            )
        
        try:
            entity = Entity.objects.get(id=entity_id)
            
            if not entity.is_active or entity.status != 'active':
                return JsonResponse(
                    {'error': 'Entity is not active'},
                    status=403
                )
            
            request.entity = entity
            
        except Entity.DoesNotExist:
            return JsonResponse(
                {'error': 'Entity not found'},
                status=404
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def entity_context_required(view_func):
    """
    Decorator to ensure entity context is set.
    
    Usage:
        @entity_context_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'entity') or not request.entity:
            return JsonResponse(
                {'error': 'Entity context required'},
                status=400
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper

def log_entity_action(action_name):
    """
    Decorator to log entity actions.
    
    Usage:
        @log_entity_action('update_settings')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .models import EntityAuditLog
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Log action if entity context exists
            if hasattr(request, 'entity') and request.entity:
                try:
                    # Get IP address
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip_address = x_forwarded_for.split(',')[0]
                    else:
                        ip_address = request.META.get('REMOTE_ADDR')
                    
                    EntityAuditLog.objects.create(
                        entity=request.entity,
                        user=request.user if request.user.is_authenticated else None,
                        action=action_name,
                        description=f"Action: {action_name}",
                        ip_address=ip_address,
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                except Exception as e:
                    logger.error(f"Failed to log entity action: {str(e)}")
            
            return response
        
        return wrapper
    return decorator