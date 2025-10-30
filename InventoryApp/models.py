from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager
import re
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.utils.crypto import get_random_string
from django.utils import timezone
from .roles import (
    VALID_ROLES, DEFAULT_ROLE, normalize_role,
    ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_USER
)

# Change VALID_ROLES to only lowercase values
# VALID_ROLES = ['admin', 'user', 'manager', 'viewer']
# DEFAULT_ROLE = 'user'

# Define a function to generate the token
def generate_invitation_token():
    return get_random_string(32) 

class Invitation(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=50)
    token = models.CharField(max_length=100, unique=True)
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation for {self.email} ({self.role})"

# Create your models here.
class Category(models.Model):
    category = models.CharField(max_length=100, unique=True)
    category_slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.category_slug:
            self.category_slug = slugify(self.category)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category

    class Meta:
        verbose_name_plural = "Categories"
    
    
class SubCategory(models.Model):
    sub_category = models.CharField(max_length=250, unique=True, db_index=True)
    sub_category_slug = models.SlugField(max_length=250, unique=True, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.sub_category_slug = slugify(self.sub_category)
        return super().save(*args, **kwargs)
    
    def subcategory_url(self):
        return reverse('App:Comp_by_Subcategory', args=[self.category.category_slug, self.sub_category_slug])

    def __str__(self):
        return '{}'.format(self.sub_category)
  
class LocationFormatField(models.CharField):
    description = 'Format: B3-B2-01'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 8
        kwargs['default'] = 'A1-A1-00'
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None:
            return value
        if not isinstance(value, str):
            value = str(value)
        if not re.match(r'^[A-Za-z0-9]+-[A-Za-z0-9]+(-\d{2})?$', value):
            return 'A1-A1-00'  # Return default instead of raising error
        return value.upper()

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)
    
    def get_prep_value(self, value):
        return str(value)  



class Component(models.Model):
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='components'
    )
    sub_category = models.ForeignKey(
        'SubCategory', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='components'
    )
    name = models.CharField(max_length=250, blank=False, db_index=True)
    comp_description = models.TextField(blank=True)
    tags = TaggableManager(blank=True)  # Add blank=True to make it optional
    component_location = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    datasheet = models.URLField(blank=True, default='')
    library = models.URLField(blank=True, default='')
    package = models.CharField(max_length=25, blank=True, default='')
    is_mtm = models.BooleanField(default=False)
    is_returnable = models.BooleanField(default=True)
    returnable = models.BooleanField(default=True)  
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Make price optional
    min_quantity = models.IntegerField(default=5)
    

    request_count = models.IntegerField(default=0)  # To track frequency
    last_requested = models.DateTimeField(auto_now=True)
    
    
    CHOICES = (
        ('upload', 'Upload Image'),
        ('link', 'Add Link')
    )

    image_option = models.CharField(max_length=10, choices=CHOICES, null=True, default='link')
    comp_image = models.ImageField(upload_to='component', blank=True, null=True)
    image_link = models.URLField(blank=True)

    RETURN_STATUS_CHOICES = [
        ('Returned', 'Returned'),
        ('Defective', 'Defective'),
        ('To be Returned', 'To be Returned'),
    ]
    return_status = models.CharField(
        max_length=20,
        choices=RETURN_STATUS_CHOICES,
        default='Returned'
    )
    
    def save(self, *args, **kwargs):
        self.is_returnable = self.returnable 
        super().save(*args, **kwargs)
    
    def save(self, *args, **kwargs):

        if self.image_option == 'upload':
            self.image_link = ''
        elif self.image_option == 'link':
            self.comp_image = None

        super().save(*args, **kwargs)

    def update_return_status(self, new_status):
        """Helper method to update return status"""
        self.return_status = new_status
        self.is_returnable = new_status in ['DEFECTIVE', 'TO_BE_RETURNED']
        self.save()
        return self

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.min_quantity:
            return "Low Stock"
        return "In Stock"

    # Add a method to get a numeric status code
    @property
    def stock_status_code(self):
        if self.quantity == 0:
            return 0  # Out of Stock
        elif self.quantity <= self.min_quantity:
            return 1  # Low Stock
        return 2  # In Stock

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ['-request_count']  # Order by most requested



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        default=DEFAULT_ROLE,
        choices=[
            (ROLE_SUPERADMIN, 'Super Admin'),
            (ROLE_ADMIN, 'Admin'),
            (ROLE_USER, 'User'),
        ]
    )
    invitation_accepted = models.BooleanField(default=False)

    def clean(self):
        if not self.role:
            self.role = DEFAULT_ROLE
        normalized_role = normalize_role(self.role)
        if normalized_role not in VALID_ROLES:
            raise ValidationError({'role': f'Invalid role: {self.role}'})
        self.role = normalized_role

    def is_superadmin(self):
        return self.role == ROLE_SUPERADMIN

    def is_admin(self):
        return self.role == ROLE_ADMIN

    def is_user(self):
        return self.role == ROLE_USER

    def has_role_permission(self, required_role):
        """Check if user has permissions of required role"""
        return required_role in ROLE_HIERARCHY.get(self.role, [])

    def save(self, *args, **kwargs):
        if not self.role:
            self.role = DEFAULT_ROLE
        self.role = self.role.lower()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def normalized_role(self):
        return self.role.lower()

    def __str__(self):
        return f"{self.user.username}'s profile - {self.role}"

    class Meta:
        db_table = 'user_profile'

# Re-enable and update the signal handlers
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create or get UserProfile when User is created"""
    if created:
        # Set superadmin role for first user
        if User.objects.count() == 1:
            UserProfile.objects.create(user=instance, role=ROLE_SUPERADMIN)
        else:
            UserProfile.objects.create(user=instance, role=ROLE_USER)

# Remove or update the save_user_profile signal as it's no longer needed

class UserInvitation(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=100)
    role = models.CharField(max_length=20)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.role:
            self.role = self.role.lower()
            if self.role not in VALID_ROLES:
                raise ValueError(f"Invalid role: {self.role}")
        super().save(*args, **kwargs)
        
class Request(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'), 
            ('REJECTED', 'Rejected')
        ],
        default='PENDING'
    )
    return_status = models.CharField(
        max_length=20, 
        default='NOT_APPLICABLE'
    )

    def __str__(self):
        return f"Request #{self.id} - {self.component.name} by {self.user.username}"

    def clean(self):
        # Validate the requested quantity is available
        if self.status == 'PENDING' and self.component.quantity < self.quantity:
            raise ValidationError('Requested quantity exceeds available stock.')

class RequestItem(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='items')






