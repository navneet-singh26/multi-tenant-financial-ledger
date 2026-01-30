
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .models import Entity, EntityMembership
import logging

logger = logging.getLogger(__name__)


class EntityContextMiddleware(MiddlewareMixin):
    """
    Middleware to set entity context for requests.
    Extracts entity from request headers or query parameters.
    """
    
    def process_request(self, request):
        """Process incoming request to set entity context."""
        
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            request.entity = None
            return None
        
        # Get entity ID from header or query parameter
        entity_id = (
            request.headers.get('X-Entity-ID') or
            request.GET.get('entity_id')
        )
        
        if not entity_id:
            request.entity = None
            return None
        
        try:
            # Get entity and verify user has access
            entity = Entity.objects.get(id=entity_id)
            
            # Check if user is a member
            membership = EntityMembership.objects.filter(
                entity=entity,
                user=request.user,
                status='active'
            ).first()
            
            if membership:
                request.entity = entity
                request.entity_membership = membership
            else:
                request.entity = None
                request.entity_membership = None
                
        except Entity.DoesNotExist:
            request.entity = None
            request.entity_membership = None
        
        return None
    
    def process_response(self, request, response):
        """Add entity context to response headers."""
        if hasattr(request, 'entity') and request.entity:
            response['X-Entity-ID'] = str(request.entity.id)
            response['X-Entity-Name'] = request.entity.name
        
        return response


class EntityPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to enforce entity-level permissions.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check entity permissions before view execution."""
        
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
        
        # Skip if no entity context
        if not hasattr(request, 'entity') or not request.entity:
            return None
        
        # Get required permission from view
        required_permission = getattr(view_func, 'required_entity_permission', None)
        
        if not required_permission:
            return None
        
        # Check if user has permission
        if not hasattr(request, 'entity_membership'):
            return JsonResponse(
                {'error': 'Access denied: Not a member of this entity'},
                status=403
            )
        
        membership = request.entity_membership
        
        if not getattr(membership, required_permission, False):
            return JsonResponse(
                {'error': f'Access denied: Missing permission {required_permission}'},
                status=403
            )
        
        return None


class EntityAuditMiddleware(MiddlewareMixin):
    """
    Middleware to log entity-related actions.
    """
    
    def process_response(self, request, response):
        """Log entity actions after response."""
        
        # Only log for authenticated users with entity context
        if not request.user.is_authenticated:
            return response
        
        if not hasattr(request, 'entity') or not request.entity:
            return response
        
        # Only log state-changing methods
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return response
        
        # Only log successful responses
        if response.status_code >= 400:
            return response
        
        try:
            from .models import EntityAuditLog
            
            # Determine action from method and path
            action = f"{request.method} {request.path}"
            
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Create audit log
            EntityAuditLog.objects.create(
                entity=request.entity,
                user=request.user,
                action=action,
                description=f"User {request.user.email} performed {action}",
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
        
        return response