from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from .roles import ROLE_SUPERADMIN, ROLE_USER

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create or get UserProfile when User is created"""
    # Only create profile if one doesn't already exist
    if not UserProfile.objects.filter(user=instance).exists():
        if created:
            # Set superadmin role for first user
            if User.objects.count() == 1:
                UserProfile.objects.create(user=instance, role=ROLE_SUPERADMIN)
            else:
                UserProfile.objects.create(user=instance, role=ROLE_USER)
