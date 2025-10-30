from django.contrib import admin
from InventoryApp.models import *

# Register your models here.

try:
    admin.site.register(Category)
    admin.site.register(SubCategory)
    admin.site.register(Component)
    admin.site.register(Invitation)
except admin.sites.AlreadyRegistered:
    pass

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')  
    search_fields = ('user__username', 'role') 

