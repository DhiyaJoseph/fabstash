from django.contrib import admin
from .models import ConsumerSession, SessionComponents, Cart

@admin.register(ConsumerSession)
class ConsumerSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_added')
    list_filter = ('date_added',)
    search_fields = ('user__username',)

@admin.register(SessionComponents)
class SessionComponentsAdmin(admin.ModelAdmin):
    list_display = ('session', 'component', 'component_quantity')
    list_filter = ('session', 'component')
    search_fields = ('component__name',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'component', 'component_quantity', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'component__name')