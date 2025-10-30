import logging
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from InventoryApp.models import Component
from InventoryConsumer.models import ConsumerSession, SessionComponents
from InventoryManager.models import RequestedItem, ComponentRequests
from django.db import transaction
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
from django.template.loader import get_template
from .api import CartView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Cart
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

class RequestLogPermission(BasePermission):
    def has_permission(self, request, view):
        # Allow access if user is authenticated
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow superadmin and admin to access all requests
        if request.user.is_superuser or request.user.is_staff:
            return True
        # Allow users to access only their own requests
        return obj.user == request.user

# Create your views here.
def add_session_component(request, component_id):

    if not request.user.is_authenticated:
        return HttpResponse('User Not Logged In', status=401)
    
    else:
        component = Component.objects.get(id=component_id)

        try:
            session = ConsumerSession.objects.get(user=request.user.id)
        except ConsumerSession.DoesNotExist:
            session = ConsumerSession.objects.create(user=request.user)

        try:
            component_request = SessionComponents.objects.get(session=session, component=component)
            if component_request.component_quantity < component_request.component.quantity:
                component_request.component_quantity += 1
                component_request.save()
        except SessionComponents.DoesNotExist:
            component_request = SessionComponents.objects.create(
                session=session,
                component=component,
                component_quantity=1
                )
            component_request.save()

        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            component_list = SessionComponents.objects.filter(session=session)
            component_count = 0
            component_qty = []
            for component in component_list:
                component_count += component.component_quantity
                component_qty.append(component.component_quantity)

            data = {
                'component_count': component_count,
                'component_quantity': component_request.component_quantity,
            }
            return JsonResponse(data)
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        

def remove_session_component(request, component_id):
    if not request.user.is_authenticated:
        return HttpResponse('Use Not Logged In', status = 401)
    else:
        if request.META.get('HTTP_X_REQUESTED_WITH') != 'XMLHttpRequest':
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        session = ConsumerSession.objects.get(user=request.user)
        components = SessionComponents.objects.filter(session=session)

        count = sum(component.component_quantity for component in components)

        try:
            session_component = components.get(component__id=component_id)
        except SessionComponents.DoesNotExist:
            return JsonResponse({'component_quantity': 0, 'session_quantity': count})

        session_quantity = session_component.component_quantity
        if session_quantity >= 1:
            session_component.component_quantity -= 1
            session_component.save()
            count -= 1
            session_quantity = session_component.component_quantity

        if session_quantity == 0:
            session_component.delete()
            return JsonResponse({'component_quantity': 0, 'session_quantity': count})

        return JsonResponse({'component_quantity': session_quantity, 'session_quantity': count})
        

def full_remove_session_component(request, component_id):
    component = SessionComponents.objects.get(id=component_id)
    component.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@csrf_exempt
@login_required
def component_request(request):
    if request.method == 'POST':
        try:
            session = ConsumerSession.objects.get(user=request.user)
            cart_items = session.sessioncomponents_set.all()

            if not cart_items.exists():
                return JsonResponse({'error': 'Cart is empty'}, status=400)

            # Create request
            comp_request = ComponentRequest.objects.create(
                user=request.user,
                request_date=timezone.now(),
                status='Pending'
            )

            # Create requested components
            for cart_item in cart_items:
                RequestedComponent.objects.create(
                    request=comp_request,
                    component=cart_item.component,
                    quantity=cart_item.component_quantity
                )

            # Clear the cart
            cart_items.delete()

            return JsonResponse({'message': 'Request submitted successfully'})

        except ConsumerSession.DoesNotExist:
            return JsonResponse({'error': 'No active cart found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

    
def session_open(request):
    try:
        session = ConsumerSession.objects.get(user=request.user.id)
    except ConsumerSession.DoesNotExist:
        session = ConsumerSession.objects.create(user=request.user.id)

    try:
        session_components = SessionComponents.objects.filter(session=session)
        session_list = []
        for component in session_components:
            if component.component.comp_image:
                image = component.component.comp_image.url
            else:
                image = component.component.image_link
            session_components_data = {
                'session_component_id': component.id,
                'component_id': component.component.id,
                'component': component.component.name,
                'category': component.component.category.category,
                'sub_category': component.component.sub_category.sub_category,
                'component_quantity': component.component_quantity,
                'component_location': component.component.component_location,
                'comp_image': image,
            }
            session_list.append(session_components_data)
    except SessionComponents.DoesNotExist:
        session_list = []

    return JsonResponse(session_list, safe=False, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_request_log(request):
    try:
        print(f"User requesting log: {request.user}")  # Debug print
        requests = ComponentRequests.objects.filter(user=request.user).order_by('-date_of_request')
        
        data = []
        for req in requests:
            for item in req.requesteditem_set.all():
                data.append({
                    'id': req.id,
                    'created_at': req.date_of_request,
                    'component_name': item.component.name,
                    'component_quantity': item.component_quantity,
                    'existing_quantity': item.component.quantity,
                    'location': item.component.component_location,
                    'status': item.status,
                    'returnable': item.component.returnable,
                    'price': str(item.component.cost),            
                    'status': req.status,
                })
        
        return Response({
            'success': True,
            'data': data
        })
    except Exception as e:
        print(f"Error in student_request_log: {str(e)}")  # Debug print
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([RequestLogPermission])
def specific_request_log(request, request_id):
    try:
        request_log = ComponentRequests.objects.get(id=request_id)
        
        # Check if user has permission to view this request
        if not RequestLogPermission().has_object_permission(request, None, request_log):
            return Response(
                {'error': 'You do not have permission to view this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        requested_items = request_log.requesteditem_set.all()
        response_data = {
            'id': request_log.id,
            'user': request_log.user.username,
            'date_of_request': request_log.date_of_request,
            'status': request_log.status,
            'items': [{
                'component_name': item.component.name,
                'quantity': item.component_quantity,
                'existing_quantity': item.component.quantity,
                'location': item.component.component_location,
                'status': item.status
            } for item in requested_items]
        }
        
        return Response(response_data)
    except ComponentRequests.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


def request_pdf(request, request_id):
    log = get_object_or_404(ComponentRequests, id=request_id)

    template_path = 'request_pdf.html'
    template = get_template(template_path)

    total_cost = sum(item['component__cost'] * item['quantity'] for item in log.requesteditem_set.values('component__cost', 'quantity'))
    context = {'log':log, 'total_cost': total_cost}

    rendered_template = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="request_log_{log.id}.pdf"'

    pisa_status = pisa.CreatePDF(rendered_template, dest=response, settings={'page_size': 'A4', 'landscape': True})

    if pisa_status.err:
        print(pisa_status.err)

    return response

    # p = canvas.Canvas(response)

    # # Add title
    # p.setFont("Helvetica", 16)
    # p.absolutePosition(0, 800)
    # p.drawString(100, 800, 'Request Log')
    # p.line(120, 45, 120 + 100, 45)
    # # Add user information
    # p.setFont("Helvetica", 12)
    # p.drawString(100, 780, f'Username: {log.user.username}')
    # p.drawString(100, 760, f'Email: {log.user.email}')

    # # Add requested items information
    # p.setFont("Helvetica", 12)
    # p.drawString(100, 740, 'Requested Items:')
    # y_position = 720
    # for item in log.requesteditem_set.all():
    #     p.drawString(120, y_position, f'Component: {item.component.name}')
    #     p.drawString(120, y_position - 20, f'Cost: {item.component.cost}')
    #     p.drawString(120, y_position - 40, f'Quantity: {item.quantity}')
    #     y_position -= 60

    # p.save()

    # return response

class ComponentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            with transaction.atomic():
                # Get user's cart
                session = ConsumerSession.objects.get(user=request.user)
                cart_items = session.sessioncomponents_set.all()

                if not cart_items.exists():
                    return Response(
                        {"error": "Cart is empty"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create component request
                component_request = ComponentRequest.objects.create(
                    user=request.user,
                    request_date=timezone.now(),
                    status='Pending'
                )

                # Create requested components from cart items
                for cart_item in cart_items:
                    RequestedComponent.objects.create(
                        request=component_request,
                        component=cart_item.component,
                        quantity=cart_item.component_quantity
                    )

                # Clear the cart
                cart_items.delete()

                # Serialize and return the created request
                serializer = ComponentRequestSerializer(component_request)
                return Response({
                    "message": "Request submitted successfully",
                    "request": serializer.data
                }, status=status.HTTP_201_CREATED)

        except ConsumerSession.DoesNotExist:
            return Response(
                {"error": "No active cart found"},
            )

class ClearCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get user's cart and delete all items
            Cart.objects.filter(user=request.user).delete()
            return Response({
                "message": "Cart cleared successfully"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": "Failed to clear cart",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_log(request):
    try:
        requests = ComponentRequests.objects.filter(user=request.user)\
            .select_related('user')\
            .prefetch_related(
                'requesteditem_set',
                'requesteditem_set__component'
            )

        data = []
        for req in requests:
            for item in req.requesteditem_set.all():
                data.append({
                    'id': req.id,
                    'created_at': req.date_of_request,
                    'status': req.status,
                    'component_name': item.component.name,
                    'quantity': item.component_quantity,
                    # Add these explicit field mappings
                    'existing_quantity': item.component.quantity,  # From Component model
                    'location': item.component.component_location,  # From Component model
                    'price': str(item.component.cost),  # From Component model
                })

        return Response({
            'success': True,
            'data': data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)