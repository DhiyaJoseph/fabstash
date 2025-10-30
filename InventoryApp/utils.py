from django.contrib.auth.models import Group
from django.db import transaction

@transaction.atomic
def create_default_groups():
    """Create default groups if they don't exist"""
    default_groups = ['Admin', 'User', 'Manager']
    
    for group_name in default_groups:
        Group.objects.get_or_create(name=group_name)
