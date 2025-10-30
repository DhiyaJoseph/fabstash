from django.db import models
from InventoryApp.models import Component
from django.contrib.auth.models import User

# Create your models here.
class ComponentRequests(models.Model):
    user = models.ForeignKey(User,null=True, on_delete=models.CASCADE)

    choices = (
        ('Rejected', 'Rejected'),
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    )
    status = models.CharField(max_length=100, choices=choices, default='Pending')
    date_of_request = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'component_request'

    def __str__(self):
        return '{}'.format(self.user.username)



class RequestedItem(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Defective', 'Defective'),
        ('To be Returned', 'To be Returned'),
        ('Returned', 'Returned'),
    ]
    
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    component_request = models.ForeignKey(ComponentRequests, on_delete=models.CASCADE)
    component_quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    return_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,  # Use the same choices as status
        default='Pending',
        null=True,
        blank=True
    )
    date_of_request = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    return_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'requested_item'
    
    def __str__(self):
        return '{} : - : {}'.format(self.component, self.component_request)

