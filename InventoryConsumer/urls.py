from django.urls import path
from InventoryConsumer import views
from .views import CartView, ClearCartView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = 'Consumer'

urlpatterns = [
    # New DRF Cart API Endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartView.as_view(), name='add_to_cart'), 
    path('cart/remove/', CartView.as_view(), name='remove_from_cart'),  
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),  
    path('request_component/', views.component_request, name='requestComponents'),
    
    
    path('request_log/<int:request_id>/', views.specific_request_log, name='specific-request-log'),
    path('api/request-log/', views.student_request_log, name='student-request-log'),
    
]

