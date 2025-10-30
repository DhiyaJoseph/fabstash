from django.db import models
from InventoryApp.models import Component
from django.contrib.auth.models import User

# Create your models here.

class ConsumerSession(models.Model):
    # session_id = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(User, null=True, on_delete = models.CASCADE)
    date_added = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'consumer_session'
        ordering = ['-date_added']

    def __str__(self):
        return self.user.username

class SessionComponents(models.Model):
    session = models.ForeignKey(ConsumerSession, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    component_quantity = models.IntegerField(default=0)  # Default value to ensure it's never NULL

    class Meta:
        db_table = 'session_components'

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    component_quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart'
        unique_together = ('user', 'component')

    def __str__(self):
        return f"{self.user.username}'s cart - {self.component.name}"




