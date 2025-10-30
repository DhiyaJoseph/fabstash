from django.urls import path
from . import views
from .views import (
    ComponentListView,
    CategoryListCreateView, 
    SubCategoryListView,
    CategoryDetailView,
    LoginView, 
    SendInvitationView, 
    AcceptInvitationView,
    accept_invitation,
    UserListView,
    CategoryListView,
    ComponentCreateAPIView,
    ComponentDetailView,
    VerifyInvitationView ,
    update_return_status,
    CategoryCreateView,
    SubCategoryCreateView,
)
from rest_framework_simplejwt.views import TokenRefreshView 

app_name = 'App'

urlpatterns = [
    path('', views.all_components, name='AllComponents'),

    path('api/categories/', CategoryListView.as_view(), name='category-list'),  
    path('api/components/', ComponentListView.as_view(), name='component-list'), 
    path('api/frequent-components/', views.frequent_components, name='frequent-components'),
    path('api/subcategories/', SubCategoryListView.as_view(), name='subcategory-list'),
    path('api/categories/create/', CategoryCreateView.as_view(), name='category-create'),
    path('api/subcategories/create/', SubCategoryCreateView.as_view(), name='subcategory-create'),
    path('api/components/mtm', ComponentListView.as_view(), name='component-mtm-list'),
   
    path('api/track-component/<int:component_id>/', views.track_component_request, name='track-component'),
    path('api/components/recent/', views.recent_components, name='recent-components'),

    path('components/category/<int:category_id>/', views.components_by_category, name='Comp_by_Category'),

    path('api/send-invitation/', SendInvitationView.as_view(), name='send-invitation'),
    path('api/verify-invitation/<str:token>/', VerifyInvitationView.as_view(), name='verify-invitation'),
    path('api/accept-invitation/<str:token>/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('api/accept-invitation/<uuid:token>/', accept_invitation, name='accept_invitation'),
    path('api/users/', UserListView.as_view(), name='user-list'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/components/<int:component_id>/quantity/', views.get_component_quantity, name='component-quantity'),
    path('components/<int:component_id>/quantity/', views.get_component_quantity, name='component-quantity'),
   
    path('api/user-details/', views.UserDetailsView.as_view(), name='user-details'),
    path('components/create/', ComponentCreateAPIView.as_view(), name='component-create'),  #
    path('api/components/<int:pk>/', views.ComponentDetailView.as_view(), name='component-detail'),
    path('api/test-email/', views.test_email, name='test-email'),
    path('api/stock-status/', views.get_stock_status, name='stock-status'),
    path('api/components/<int:component_id>/return-status/',views.update_return_status, name='update_return_status'),
    path('components/', ComponentListView.as_view(), name='component-list'),
    path('api/submit-request/', views.submit_request, name='submit-request'),
    path('api/requests/', views.list_requests, name='list-requests'),
    
    # Update these URLs for request management
    path('api/manager/requests/', views.list_manager_requests, name='manager-requests'),
    path('api/manager/requests/<int:request_id>/status/', views.update_request_status, name='update-request-status'),
    path('api/manager/requests/stats/', views.get_request_stats, name='request-stats'),
]
