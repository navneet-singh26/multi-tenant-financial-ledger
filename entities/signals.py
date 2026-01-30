
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Entity, EntityMembership, EntityAuditLog, EntitySettings
from .schema_manager import SchemaManager
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Entity)
def create_entity_schema(sender, instance, created, **kwargs):
    """Create database schema when entity is created."""
    if created:
        schema_manager = SchemaManager()
        try:
            schema_manager.create_schema(instance.schema_name)
            logger.info(f"Created schema for entity: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to create schema for entity {instance.name}: {str(e)}")


@receiver(post_save, sender=Entity)
def create_entity_settings(sender, instance, created, **kwargs):
    """Create default settings when entity is created."""
    if created:
        EntitySettings.objects.get_or_create(entity=instance)
        logger.info(f"Created settings for entity: {instance.name}")


@receiver(post_save, sender=EntityMembership)
def set_owner_permissions(sender, instance, created, **kwargs):
    """Set all permissions for owner role."""
    if created and instance.role == 'owner':
        instance.can_view_financials = True
        instance.can_create_transactions = True
        instance.can_approve_transactions = True
        instance.can_manage_users = True
        instance.can_manage_settings = True
        instance.save()


@receiver(post_delete, sender=Entity)
def delete_entity_schema(sender, instance, **kwargs):
    """Delete database schema when entity is deleted."""
    schema_manager = SchemaManager()
    try:
        schema_manager.drop_schema(instance.schema_name)
        logger.info(f"Deleted schema for entity: {instance.name}")
    except Exception as e:
        logger.error(f"Failed to delete schema for entity {instance.name}: {str(e)}")

@receiver(post_save, sender=Entity)
def entity_post_save(sender, instance, created, **kwargs):
    """Handle entity creation and updates."""
    
    if created:
        logger.info(f"New entity created: {instance.name} ({instance.id})")
        
        # Create database schema
        try:
            schema_manager = SchemaManager()
            schema_manager.create_schema(instance.schema_name)
            logger.info(f"Created schema: {instance.schema_name}")
        except Exception as e:
            logger.error(f"Failed to create schema for entity {instance.id}: {str(e)}")
        
        # Create audit log
        EntityAuditLog.objects.create(
            entity=instance,
            action='entity_created',
            description=f"Entity {instance.name} was created"
        )
    else:
        logger.info(f"Entity updated: {instance.name} ({instance.id})")
        
        # Create audit log for updates
        EntityAuditLog.objects.create(
            entity=instance,
            action='entity_updated',
            description=f"Entity {instance.name} was updated"
        )


@receiver(pre_delete, sender=Entity)
def entity_pre_delete(sender, instance, **kwargs):
    """Handle entity deletion preparation."""
    
    logger.warning(f"Entity being deleted: {instance.name} ({instance.id})")
    
    # Create final audit log
    EntityAuditLog.objects.create(
        entity=instance,
        action='entity_deleted',
        description=f"Entity {instance.name} is being deleted"
    )


@receiver(post_delete, sender=Entity)
def entity_post_delete(sender, instance, **kwargs):
    """Handle entity deletion cleanup."""
    
    # Drop database schema
    try:
        schema_manager = SchemaManager()
        schema_manager.drop_schema(instance.schema_name)
        logger.info(f"Dropped schema: {instance.schema_name}")
    except Exception as e:
        logger.error(f"Failed to drop schema {instance.schema_name}: {str(e)}")


@receiver(post_save, sender=EntityMembership)
def membership_post_save(sender, instance, created, **kwargs):
    """Handle membership creation and updates."""
    
    if created:
        logger.info(
            f"New membership: {instance.user.email} added to {instance.entity.name} "
            f"as {instance.role}"
        )
        
        # Send invitation email if status is invited
        if instance.status == 'invited':
            try:
                send_invitation_email(instance)
            except Exception as e:
                logger.error(f"Failed to send invitation email: {str(e)}")
        
        # Create audit log
        EntityAuditLog.objects.create(
            entity=instance.entity,
            user=instance.user,
            action='member_added',
            description=f"User {instance.user.email} added as {instance.role}"
        )
    else:
        # Check if role or status changed
        if instance.tracker.has_changed('role'):
            old_role = instance.tracker.previous('role')
            EntityAuditLog.objects.create(
                entity=instance.entity,
                user=instance.user,
                action='role_changed',
                description=f"Role changed from {old_role} to {instance.role}",
                changes={
                    'old_role': old_role,
                    'new_role': instance.role
                }
            )
        
        if instance.tracker.has_changed('status'):
            old_status = instance.tracker.previous('status')
            EntityAuditLog.objects.create(
                entity=instance.entity,
                user=instance.user,
                action='status_changed',
                description=f"Status changed from {old_status} to {instance.status}",
                changes={
                    'old_status': old_status,
                    'new_status': instance.status
                }
            )


@receiver(post_delete, sender=EntityMembership)
def membership_post_delete(sender, instance, **kwargs):
    """Handle membership deletion."""
    
    logger.info(
        f"Membership removed: {instance.user.email} from {instance.entity.name}"
    )
    
    # Create audit log
    EntityAuditLog.objects.create(
        entity=instance.entity,
        user=instance.user,
        action='member_removed',
        description=f"User {instance.user.email} removed from entity"
    )


def send_invitation_email(membership):
    """Send invitation email to new member."""
    
    subject = f"Invitation to join {membership.entity.name}"
    
    message = f"""
    Hello,
    
    You have been invited to join {membership.entity.name} as a {membership.role}.
    
    Please log in to accept this invitation.
    
    Best regards,
    {membership.entity.name} Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[membership.user.email],
        fail_silently=False
    )
