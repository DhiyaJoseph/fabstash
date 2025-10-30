"""InventoryTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from InventoryTracker import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from InventoryApp.views import LoginView, SubCategoryListView, get_user_details
from InventoryApp.views import update_return_status

urlpatterns = [
    # Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', LoginView.as_view(), name='login'),  # Changed from api/login/
    
    # Rest of your URLs
    path('admin/', admin.site.urls),
    path('api/', include('InventoryManager.urls')),  # This ensures all API routes are under /api/
    path('', include('InventoryApp.urls', namespace='inventory')),
    path('consumer/', include('InventoryConsumer.urls', namespace='inventory_consumer')),
    path('manager/', include('InventoryManager.urls', namespace='inventory_manager')),
    path('api/manager/', include('InventoryManager.urls')),  # Add this line
    path('search/', include('InventorySearch.urls')),
    path('Consumer/', include('InventoryConsumer.urls')),  # Add this line
]  

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass
