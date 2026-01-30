
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from .models import Entity, EntityMembership, EntitySettings, EntityAuditLog
from .serializers import (
    EntitySerializer, EntityListSerializer, EntityMembershipSerializer,
    InviteMemberSerializer, EntitySettingsSerializer, EntityAuditLogSerializer,
    EntityStatisticsSerializer
)
from .permissions import IsEntityOwnerOrAdmin, IsEntityMember
from .schema_manager import SchemaManager
import logging

logger = logging.getLogger(__name__)


class EntityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing entities.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return entities where user is a member."""
        user = self.request.user
        if user.is_superuser:
            return Entity.objects.all()
        
        return Entity.objects.filter(
            memberships__user=user,
            memberships__status='active'
        ).distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return EntityListSerializer
        return EntitySerializer
    
    def perform_create(self, serializer):
        """Create entity with audit log."""
        entity = serializer.save()
        
        # Log entity creation
        EntityAuditLog.objects.create(
            entity=entity,
            user=self.request.user,
            action='created',
            description=f"Entity '{entity.name}' created",
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT')
        )
    
    def perform_update(self, serializer):
        """Update entity with audit log."""
        entity = serializer.save()
        
        # Log entity update
        EntityAuditLog.objects.create(
            entity=entity,
            user=self.request.user,
            action='updated',
            description=f"Entity '{entity.name}' updated",
            changes=serializer.validated_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT')
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsEntityOwnerOrAdmin])
    def activate(self, request, pk=None):
        """Activate an entity."""
        entity = self.get_object()
        entity.status = 'active'
        entity.is_active = True
        entity.activated_at = timezone.now()
        entity.save()
        
        # Log activation
        EntityAuditLog.objects.create(
            entity=entity,
            user=request.user,
            action='activated',
            description=f"Entity '{entity.name}' activated",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'status': 'Entity activated'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsEntityOwnerOrAdmin])
    def deactivate(self, request, pk=None):
        """Deactivate an entity."""
        entity = self.get_object()
        entity.status = 'inactive'
        entity.is_active = False
        entity.save()
        
        # Log deactivation
        EntityAuditLog.objects.create(
            entity=entity,
            user=request.user,
            action='deactivated',
            description=f"Entity '{entity.name}' deactivated",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'status': 'Entity deactivated'})
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get entity statistics."""
        entity = self.get_object()
        
        stats = {
            'total_members': entity.memberships.count(),
            'active_members': entity.memberships.filter(status='active').count(),
            'pending_invitations': entity.memberships.filter(status='invited').count(),
            'total_transactions': 0,  # Will be implemented with ledger
            'last_activity': entity.audit_logs.first().created_at if entity.audit_logs.exists() else None
        }
        
        serializer = EntityStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def audit_logs(self, request, pk=None):
        """Get entity audit logs."""
        entity = self.get_object()
        logs = entity.audit_logs.all()[:100]  # Last 100 logs
        serializer = EntityAuditLogSerializer(logs, many=True)
        return Response(serializer.data)
    

class EntityMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing entity memberships.
    """
    serializer_class = EntityMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsEntityMember]
    
    def get_queryset(self):
        """Return memberships for entities where user is a member."""
        user = self.request.user
        entity_id = self.request.query_params.get('entity_id')
        
        queryset = EntityMembership.objects.select_related('entity', 'user', 'invited_by')
        
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        else:
            # Return memberships for entities where user is a member
            user_entities = Entity.objects.filter(
                memberships__user=user,
                memberships__status='active'
            )
            queryset = queryset.filter(entity__in=user_entities)
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[IsEntityOwnerOrAdmin])
    def invite(self, request):
        """Invite a user to join an entity."""
        entity_id = request.data.get('entity_id')
        entity = get_object_or_404(Entity, id=entity_id)
        
        # Check if user has permission to invite
        membership = entity.memberships.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not membership or not membership.can_manage_users:
            return Response(
                {'error': 'You do not have permission to invite users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InviteMemberSerializer(
            data=request.data,
            context={'request': request, 'entity': entity}
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        
        # Log invitation
        EntityAuditLog.objects.create(
            entity=entity,
            user=request.user,
            action='member_added',
            description=f"Invited {membership.user.email} as {membership.role}",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response(
            EntityMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def accept_invitation(self, request, pk=None):
        """Accept an entity invitation."""
        membership = self.get_object()
        
        if membership.user != request.user:
            return Response(
                {'error': 'You cannot accept this invitation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if membership.status != 'invited':
            return Response(
                {'error': 'This invitation is no longer valid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.status = 'active'
        membership.invitation_accepted_at = timezone.now()
        membership.save()
        
        # Log acceptance
        EntityAuditLog.objects.create(
            entity=membership.entity,
            user=request.user,
            action='member_added',
            description=f"{request.user.email} accepted invitation",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'status': 'Invitation accepted'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsEntityOwnerOrAdmin])
    def remove(self, request, pk=None):
        """Remove a member from an entity."""
        membership = self.get_object()
        entity = membership.entity
        
        # Check if user has permission
        requester_membership = entity.memberships.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not requester_membership or not requester_membership.can_manage_users:
            return Response(
                {'error': 'You do not have permission to remove members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot remove owner
        if membership.role == 'owner':
            return Response(
                {'error': 'Cannot remove entity owner'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_email = membership.user.email
        membership.delete()
        
        # Log removal
        EntityAuditLog.objects.create(
            entity=entity,
            user=request.user,
            action='member_removed',
            description=f"Removed {user_email} from entity",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'status': 'Member removed'})
    

    @action(detail=True, methods=['patch'], permission_classes=[IsEntityOwnerOrAdmin])
    def update_role(self, request, pk=None):
        """Update a member's role and permissions."""
        membership = self.get_object()
        entity = membership.entity
        
        # Check if user has permission
        requester_membership = entity.memberships.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not requester_membership or not requester_membership.can_manage_users:
            return Response(
                {'error': 'You do not have permission to update member roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot change owner role
        if membership.role == 'owner':
            return Response(
                {'error': 'Cannot change owner role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = EntityMembershipSerializer(
            membership,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Log role change
        EntityAuditLog.objects.create(
            entity=entity,
            user=request.user,
            action='member_role_changed',
            description=f"Updated role for {membership.user.email}",
            changes=request.data,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response(serializer.data)


class EntitySettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing entity settings.
    """
    serializer_class = EntitySettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsEntityMember]
    
    def get_queryset(self):
        """Return settings for entities where user is a member."""
        user = self.request.user
        entity_id = self.request.query_params.get('entity_id')
        
        queryset = EntitySettings.objects.select_related('entity')
        
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        else:
            # Return settings for entities where user is a member
            user_entities = Entity.objects.filter(
                memberships__user=user,
                memberships__status='active'
            )
            queryset = queryset.filter(entity__in=user_entities)
        
        return queryset
    
    def perform_update(self, serializer):
        """Update settings with audit log."""
        settings = serializer.save()
        
        # Log settings update
        EntityAuditLog.objects.create(
            entity=settings.entity,
            user=self.request.user,
            action='settings_updated',
            description=f"Updated settings for entity '{settings.entity.name}'",
            changes=serializer.validated_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT')
        )