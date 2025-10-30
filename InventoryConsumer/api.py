from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from InventoryConsumer.models import ConsumerSession, SessionComponents
from InventoryApp.models import Component
from .serializers import SessionComponentSerializer, AddSessionComponentSerializer
from rest_framework import status
from django.db import transaction

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all items in the user's cart."""
        try:
            session = ConsumerSession.objects.get(user=request.user)
            session_components = SessionComponents.objects.filter(session=session)
            
            # Debug prints
            print(f"User: {request.user.username}")
            print(f"Session components count: {session_components.count()}")
            
            serializer = SessionComponentSerializer(session_components, many=True)
            print(f"Serialized data: {serializer.data}")  # Debug print
            
            # Set CORS headers
            response = Response(serializer.data, status=status.HTTP_200_OK)
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response
            
        except ConsumerSession.DoesNotExist:
            print(f"No session found for user: {request.user.username}")  # Debug print
            return Response([], status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in cart view: {str(e)}")  # Debug print
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Add an item to the cart."""
        serializer = AddSessionComponentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component_id = serializer.validated_data['component_id']
        quantity = serializer.validated_data['quantity']

        try:
            # Fetch component by ID, and check if there is enough stock
            component = get_object_or_404(Component, id=component_id)

            if component.quantity < quantity:
                return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)

            session, _ = ConsumerSession.objects.get_or_create(user=request.user)

            # Ensure component_quantity is set properly
            with transaction.atomic():
                session_component, created = SessionComponents.objects.get_or_create(
                    session=session, component=component
                )

                if created:
                    session_component.component_quantity = quantity
                else:
                    session_component.component_quantity += quantity

                # Ensure component_quantity is never None before saving
                if session_component.component_quantity is None:
                    session_component.component_quantity = 0  # Default to 0 if it's None

                session_component.save()

            return Response({"message": "Component added to cart"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Remove an item from the cart."""
        serializer = AddSessionComponentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        component_id = serializer.validated_data['component_id']
        quantity = serializer.validated_data['quantity']

        try:
            session = ConsumerSession.objects.get(user=request.user)
            session_component = SessionComponents.objects.get(
                session=session, 
                component__id=component_id
            )

            with transaction.atomic():
                if session_component.component_quantity <= quantity:
                    session_component.delete()
                else:
                    session_component.component_quantity -= quantity
                    session_component.save()

                # Calculate new total after removal
                new_total = sum(
                    comp.component_quantity or 0 
                    for comp in SessionComponents.objects.filter(session=session)
                )

            return Response({
                "message": "Component removed from cart",
                "total_quantity": new_total
            }, status=status.HTTP_200_OK)
            
        except ConsumerSession.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
        except SessionComponents.DoesNotExist:
            return Response({"error": "Item not in cart"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)