
from .models import Entity, EntityMembership


def entity_context(request):
    """
    Context processor to add entity information to templates.
    
    Usage in settings.py:
        TEMPLATES = [{
            'OPTIONS': {
                'context_processors': [
                    ...
                    'entities.context_processors.entity_context',
                ],
            },
        }]
    """
    context = {
        'current_entity': None,
        'user_entities': [],
        'entity_membership': None,
    }
    
    if not request.user.is_authenticated:
        return context
    
    # Get current entity from request
    if hasattr(request, 'entity') and request.entity:
        context['current_entity'] = request.entity
        
        if hasattr(request, 'entity_membership'):
            context['entity_membership'] = request.entity_membership
    
    # Get all entities user is a member of
    memberships = EntityMembership.objects.filter(
        user=request.user,
        status='active'
    ).select_related('entity').order_by('-entity__created_at')
    
    context['user_entities'] = [m.entity for m in memberships]
    
    return context