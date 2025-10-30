from django.db import transaction, OperationalError
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, F, Q
from .models import ComponentRequests, RequestedItem  # Remove Request from import
from InventoryApp.models import Component
from InventoryConsumer.models import Cart, ConsumerSession
from .serializers import ComponentRequestSerializer, RequestedItemSerializer,ComponentDetailSerializer
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser
from django.http import JsonResponse
from corsheaders.defaults import default_headers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class IsAdminOrRequestOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admin/superadmin can see all requests
        if request.user.is_staff:
            return True
        # Regular users can only see their own requests
        return obj.user == request.user

class SubmitRequestView(APIView):
    permission_classes = [IsAuthenticated]  # This ensures token is valid

    def post(self, request, *args, **kwargs):
        logger.debug(f"Received request data: {request.data}")
        logger.debug(f"Headers: {request.headers}")
        
        try:
            components = request.data.get('components', [])
            logger.debug(f"Components data: {components}")

            if not components:
                return Response({
                    "message": "No components provided."
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                component_request = ComponentRequests.objects.create(
                    user=request.user,
                    status='Pending'
                )
                logger.debug(f"Created component request: {component_request.id}")

                for item in components:
                    component_id = item.get('component_id')
                    requested_quantity = item.get('quantity')
                    logger.debug(f"Processing item: {component_id}, quantity: {requested_quantity}")
                    
                    component = Component.objects.get(id=component_id)
                    RequestedItem.objects.create(
                        component=component,
                        component_request=component_request,
                        component_quantity=requested_quantity,
                        status='Pending'
                    )

                Cart.objects.filter(user=request.user).delete()
                logger.debug("Cart cleared successfully")

                return Response({
                    "message": "Request submitted successfully",
                    "request_id": component_request.id
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error in SubmitRequestView: {str(e)}", exc_info=True)
            return Response({
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RequestListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Debug information
            print(f"User: {request.user}, Is staff: {request.user.is_staff}")
            
            # Filter requests based on user role
            if request.user.is_staff:
                queryset = ComponentRequests.objects.all()
            else:
                queryset = ComponentRequests.objects.filter(user=request.user)
            
            queryset = queryset.select_related('user')\
                .prefetch_related('requesteditem_set', 'requesteditem_set__component')\
                .order_by('-date_of_request')
                
            serializer = ComponentRequestSerializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in RequestListView: {str(e)}")
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            serializer = ComponentRequestSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("Error:", str(e))
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    def patch(self, request, request_id):
        # Only admins can update request status
        if not request.user.is_staff:
            return Response({"detail": "Only admins can update requests"}, 
                          status=status.HTTP_403_FORBIDDEN)
            
        try:
            with transaction.atomic():
                comp_request = ComponentRequests.objects.select_for_update().get(id=request_id)
                new_status = request.data.get('status')
                
                if not new_status:
                    return Response(
                        {'error': 'Status is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update main request status
                comp_request.status = new_status
                comp_request.save()
                
                # Update all associated items' status
                RequestedItem.objects.filter(component_request=comp_request).update(
                    status=new_status
                )
                
                # If approved/completed, update component quantities
                if new_status == 'Completed':
                    for item in comp_request.requesteditem_set.all():
                        component = item.component
                        component.quantity = F('quantity') - item.component_quantity
                        component.save()
                
                # Fetch updated data
                updated_items = RequestedItem.objects.filter(component_request=comp_request)
                serializer = RequestedItemSerializer(updated_items, many=True)
                
                return Response({
                    'status': 'success',
                    'request_status': new_status,
                    'items': serializer.data
                }, status=status.HTTP_200_OK)

        except ComponentRequests.DoesNotExist:
            return Response(
                {'error': 'Request not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RequestStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Base queryset depending on user role
            if request.user.is_staff:
                base_queryset = ComponentRequests.objects.all()
            else:
                base_queryset = ComponentRequests.objects.filter(user=request.user)

            stats = {
                'pending': base_queryset.filter(status='Pending').count(),
                'approved': base_queryset.filter(status__in=['Approved', 'Completed']).count(),
                'rejected': base_queryset.filter(status='Rejected').count(),
                'total': base_queryset.count(),
                'last_updated': timezone.now().isoformat()
            }
            return Response(stats)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@transaction.atomic
def submit_request(request):
    user = request.user

    if not user.is_authenticated:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    cart_items = Cart.objects.filter(user=user)
    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    # Create a new Component Request
    component_request = ComponentRequests.objects.create(user=user)

    # Create Requested Items from Cart
    for cart_item in cart_items:
        RequestedItem.objects.create(
            component=cart_item.component,
        )
    def get(self, request):
        requests = ComponentRequests.objects.all().order_by('-date_of_request')
        serializer = RequestDetailSerializer(requests, many=True)
        return Response(serializer.data)


@transaction.atomic
def submit_request(request):
    user = request.user

    if not user.is_authenticated:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    cart_items = Cart.objects.filter(user=user)
    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    # Create a new Component Request
    component_request = ComponentRequests.objects.create(user=user)

    # Create Requested Items from Cart
    for cart_item in cart_items:
        RequestedItem.objects.create(
            component=cart_item.component,
            component_request=component_request,
            component_quantity=cart_item.component_quantity
        )

    # Clear the user's cart
    cart_items.delete()

    return JsonResponse({"message": "Request submitted successfully"}, status=201)


class ComponentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def get_object(self, pk):
        print(f"Fetching Component with pk: {pk}")
        try:
            return Component.objects.get(pk=pk)
        except Component.DoesNotExist:
            print(f"Component with pk: {pk} does not exist.")
            raise Http404

    def get(self, request, pk, format=None):
        component = self.get_object(pk)
        serializer = ComponentDetailSerializer(component)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        try:
            component = self.get_object(pk)
            
            # Create a mutable copy of the data
            data = request.data.dict() if hasattr(request.data, 'dict') else request.data
            
            # Debug log
            print("Received data:", data)
            print("Files:", request.FILES)
            
            # Handle boolean fields
            if 'is_mtm' in data:
                data['is_mtm'] = str(data['is_mtm']).lower() == 'true'
            if 'returnable' in data:
                data['returnable'] = str(data['returnable']).lower() == 'true'
            
            # Handle image
            if 'comp_image' in request.FILES:
                data['comp_image'] = request.FILES['comp_image']
            
            serializer = ComponentDetailSerializer(component, data=data, partial=True)
            if serializer.is_valid():
                instance = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                {'detail': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            print("Error:", str(e))  # Debug log
            return Response(
                {'detail': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


    def delete(self, request, pk, format=None):
        component = self.get_object(pk)
        component.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ApproveRequestView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    
    def patch(self, request, request_id):
        return self._process_request(request_id)
        
    def post(self, request, request_id):
        return self._process_request(request_id)
        
    def _process_request(self, request_id):
        try:
            req = ComponentRequests.objects.get(id=request_id)
            req.status = 'Completed'
            req.save()
            
            # Update all related items
            RequestedItem.objects.filter(component_request=req).update(status='Completed')
            
            return Response({
                'status': 'success',
                'message': f'Request {request_id} approved successfully'
            }, status=status.HTTP_200_OK)
            
        except ComponentRequests.DoesNotExist:
            return Response({
                'error': 'Request not found'
            }, status=status.HTTP_404_NOT_FOUND)

class RejectRequestView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]  # Only admins can reject
    def patch(self, request, request_id):
        try:
            req = ComponentRequests.objects.get(id=request_id)
            req.status = 'Rejected'
            req.save()
            return Response({'status': 'Rejected'}, status=status.HTTP_200_OK)
        except ComponentRequests.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_request_status(request):
    request_id = request.data.get('request_id')
    new_status = request.data.get('status')
    item_ids = request.data.get('item_ids', [])

    if not request_id or not new_status:
        return Response({'error': 'Request ID and new status are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        comp_request = ComponentRequests.objects.get(id=request_id)
        if item_ids:
            # Update only specified RequestedItem records
            items = RequestedItem.objects.filter(
                component_request=comp_request, id__in=item_ids
            )
        else:
            # Update all items for this request
            items = RequestedItem.objects.filter(component_request=comp_request)

        # Set status for each item
        for it in items:
            it.status = new_status
            it.save()

        # If all items are completed or rejected, optionally update request status
        if not RequestedItem.objects.filter(
            component_request=comp_request, status='Pending'
        ).exists():
            comp_request.status = (
                'Completed' if new_status == 'Approved' else new_status
            )
            comp_request.save()

        return Response({'message': 'Bulk update successful'}, status=status.HTTP_200_OK)
    except ComponentRequests.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RequestItemStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get_stock_status(self):
        # Get components with quantity 0 (out of stock)
        out_of_stock = Component.objects.filter(quantity=0)
        # Get components where quantity is less than or equal to min_quantity (low stock)
        low_stock = Component.objects.filter(
            quantity__gt=0,
            quantity__lte=F('min_quantity')
        )

        return {
            'out_of_stock': out_of_stock,
            'low_stock': low_stock
        }

def get(self, request, request_id, item_id):
    try:
        requested_item = RequestedItem.objects.get(
            id=item_id, 
            component_request_id=request_id
        )
        serializer = RequestedItemSerializer(requested_item)
        return Response(serializer.data)
    except RequestedItem.DoesNotExist:
        return Response(
            {"error": "Item not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AdminRequestOverviewView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]  # Ensures only admin users can access
    
    def get(self, request):
        # Check if user is admin/staff
        if not request.user.is_staff:
            return Response(
                {"error": "Only administrators can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            # Get all requests with related data
            requests = ComponentRequests.objects.all()\
                .select_related('user')\
                .prefetch_related('requesteditem_set')\
                .order_by('-date_of_request')
            
            # Group by status
            overview = {
                'pending_requests': [],
                'approved_requests': [],
                'rejected_requests': [],
                'statistics': {
                    'total_requests': requests.count(),
                    'pending_count': requests.filter(status='Pending').count(),
                    'approved_count': requests.filter(status='Completed').count(),
                    'rejected_count': requests.filter(status='Rejected').count()
                }
            }
            
            for req in requests:
                request_data = {
                    'id': req.id,
                    'user': req.user.username,
                    'date': req.date_of_request,
                    'status': req.status,
                    'items_count': req.requesteditem_set.count(),
                    'total_quantity': sum(item.component_quantity for item in req.requesteditem_set.all())
                }
                
                if req.status == 'Pending':
                    overview['pending_requests'].append(request_data)
                elif req.status == 'Completed':
                    overview['approved_requests'].append(request_data)
                else:
                    overview['rejected_requests'].append(request_data)
                    
            return Response(overview)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            if request.user.is_staff:
                # Admin dashboard stats
                return Response({
                    'requests': {
                        'total': ComponentRequests.objects.count(),
                        'pending': ComponentRequests.objects.filter(status='Pending').count(),
                        'approved': ComponentRequests.objects.filter(status='Completed').count(),
                        'rejected': ComponentRequests.objects.filter(status='Rejected').count()
                    },
                    'components': {
                        'total': Component.objects.count(),
                        'low_stock': Component.objects.filter(quantity__lte=F('min_quantity')).count(),
                        'out_of_stock': Component.objects.filter(quantity=0).count()
                    },
                    'users': {
                        'total_users': User.objects.count(),
                        'active_users': User.objects.filter(is_active=True).count()
                    }
                })
            else:
                # Regular user dashboard stats
                return Response({
                    'my_requests': {
                        'total': ComponentRequests.objects.filter(user=request.user).count(),
                        'pending': ComponentRequests.objects.filter(user=request.user, status='Pending').count(),
                        'approved': ComponentRequests.objects.filter(user=request.user, status='Completed').count(),
                        'rejected': ComponentRequests.objects.filter(user=request.user, status='Rejected').count()
                    }
                })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            current_time = timezone.now()
            
            if request.user.is_staff:
                # Admin dashboard stats
                component_stats = Component.objects.aggregate(
                    total=Count('id'),
                    low_stock=Count('id', filter=Q(quantity__lte=F('min_quantity'))),
                    out_of_stock=Count('id', filter=Q(quantity=0))
                )
                
                request_stats = ComponentRequests.objects.aggregate(
                    total=Count('id'),
                    pending=Count('id', filter=Q(status='Pending')),
                    approved=Count('id', filter=Q(status='Completed')),
                    rejected=Count('id', filter=Q(status='Rejected'))
                )
                
                user_stats = User.objects.aggregate(
                    total_users=Count('id'),
                    active_users=Count('id', filter=Q(is_active=True))
                )

                return Response({
                    'requests': request_stats,
                    'components': component_stats,
                    'users': user_stats,
                    'last_updated': current_time.isoformat()
                })
            else:
                # Regular user dashboard stats
                my_requests = ComponentRequests.objects.filter(user=request.user)
                return Response({
                    'my_requests': {
                        'total': my_requests.count(),
                        'pending': my_requests.filter(status='Pending').count(),
                        'approved': my_requests.filter(status='Completed').count(),
                        'rejected': my_requests.filter(status='Rejected').count(),
                        'last_updated': current_time.isoformat()
                    }
                })
        except Exception as e:
            print(f"Dashboard Error: {str(e)}")  # Add debug print
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RequestDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, request_id):
        try:
            comp_request = ComponentRequests.objects.select_related('user').prefetch_related(
                'requesteditem_set', 
                'requesteditem_set__component'
            ).get(id=request_id)
            
            # Add detailed item information
            items = [{
                'id': item.id,
                'component_name': item.component.name,
                'component_quantity': item.component_quantity,
                'existing_quantity': item.component.quantity,
                'location': item.component.component_location,
                'status': item.status,
                'returnable': item.component.returnable,
                'price': str(item.component.cost) if item.component.cost else 'N/A'
            } for item in comp_request.requesteditem_set.all()]

            return Response({
                'id': comp_request.id,
                'status': comp_request.status,
                'date': comp_request.date_of_request,
                'user': comp_request.user.username,
                'items': items,
                'last_updated': timezone.now().isoformat()
            })
        except ComponentRequests.DoesNotExist:
            return Response({"error": "Request not found"}, status=404)
            
    def patch(self, request, request_id, item_id=None):
        print(f"PATCH request - Request ID: {request_id}, Item ID: {item_id}")
        print(f"Data received: {request.data}")
        
        try:
            with transaction.atomic():
                comp_request = ComponentRequests.objects.select_for_update().get(id=request_id)
                new_status = request.data.get('status', '').upper()
                
                if new_status not in ['PENDING', 'APPROVED', 'REJECTED', 'COMPLETED']:
                    return Response({'error': 'Invalid status'}, status=400)

                if item_id:
                    # Update single item
                    item = RequestedItem.objects.select_for_update().get(
                        component_request=comp_request,
                        id=item_id
                    )
                    old_status = item.status
                    item.status = new_status
                    item.save()
                    
                    print(f"Updated item {item_id} from {old_status} to {new_status}")
                else:
                    # Update all items
                    RequestedItem.objects.filter(component_request=comp_request).update(
                        status=new_status
                    )
                    comp_request.status = new_status
                    comp_request.save()
                    
                    print(f"Updated request {request_id} and all items to {new_status}")

                # Get updated stats
                stats = {
                    'pending': RequestedItem.objects.filter(status='PENDING').count(),
                    'approved': RequestedItem.objects.filter(status='APPROVED').count(),
                    'rejected': RequestedItem.objects.filter(status='REJECTED').count()
                }

                return Response({
                    'success': True,
                    'message': f'Status updated to {new_status}',
                    'stats': stats
                })

        except RequestedItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=404)
        except ComponentRequests.DoesNotExist:
            return Response({"error": "Request not found"}, status=404)
        except Exception as e:
            print(f"Error updating status: {str(e)}")
            return Response({"error": str(e)}, status=500)