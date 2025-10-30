from rest_framework import viewsets,generics
from .models import Category, SubCategory, Component , Invitation
from .serializers import CategorySerializer,SubCategorySerializer, ComponentSerializer,InvitationSerializer
from rest_framework.response import Response
import logging
logger = logging.getLogger(__name__)
from rest_framework.generics import ListAPIView

from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from django.http import JsonResponse

from django.conf import settings
import uuid  # For generating a unique token for the invitation link
from django.contrib.auth.models import User, Group
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)

VALID_ROLES = ['Admin', 'User', 'Superadmin'] 

class SendInvitationView(APIView):
    def post(self, request):
        email = request.data.get('email')
        role = request.data.get('role')

        if not email or not role:
            return Response({"error": "Email and role are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the email is already invited
        if Invitation.objects.filter(email=email).exists():
            return Response({"error": "This email is already invited."}, status=status.HTTP_400_BAD_REQUEST)

        # Create invitation with a unique token for the invitation link
        invitation_token = uuid.uuid4().hex
        invitation = Invitation.objects.create(email=email, role=role, token=invitation_token)

        # Send invitation email
        link = f"http://localhost:5173/accept-invitation/{invitation_token}"
        subject = "You're Invited!"
        message = f"Hello,\n\nYou've been invited to join. Click the link below to accept the invitation:\n\n{link}"
        send_mail(subject, message, settings.EMAIL_HOST_USER, [email])

        return Response({"message": "Invitation sent successfully."}, status=status.HTTP_201_CREATED)


class AcceptInvitationView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        try:
            logger.info(f"Fetching invitation with token: {token}")
            invitation = Invitation.objects.get(token=token)
            
            if invitation.is_accepted:
                return Response(
                    {"error": "This invitation has already been used."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({
                "email": invitation.email,
                "role": invitation.role
            }, status=status.HTTP_200_OK)
            
        except Invitation.DoesNotExist:
            logger.error(f"Invalid invitation token: {token}")
            return Response(
                {"error": "Invalid invitation token"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error processing invitation: {str(e)}")
            return Response(
                {"error": f"Server error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, token):
        try:
            logger.info(f"Processing invitation acceptance for token: {token}")
            invitation = Invitation.objects.get(token=token)
            
            if invitation.is_accepted:
                return Response(
                    {"error": "This invitation has already been used."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            username = request.data.get('username')
            password = request.data.get('password')

            # Validate input
            if not username or not password:
                return Response(
                    {"error": "Username and password are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(username=username).exists():
                return Response(
                    {"error": "This username is already taken."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user with profile and group
            try:
                user = User.objects.create_user(
                    username=username,
                    email=invitation.email,
                    password=password
                )

                # Create UserProfile
                UserProfile.objects.create(
                    user=user,
                    role=invitation.role
                )

                # Add to group
                group_name = invitation.role.lower()
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

                # Mark invitation as accepted
                invitation.is_accepted = True
                invitation.save()

                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)

                return Response({
                    "message": "Account created successfully",
                    "username": username,
                    "role": invitation.role,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Error creating user account: {str(e)}")
                # If there's an error, cleanup any partially created data
                if 'user' in locals():
                    user.delete()
                return Response(
                    {"error": "Failed to create account. Please try again."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Invitation.DoesNotExist:
            logger.error(f"Invalid invitation token during POST: {token}")
            return Response(
                {"error": "Invalid invitation token"}, 
                status=status.HTTP_404_NOT_FOUND
            )
   
        
class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()  # Or filter by some criteria
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

# Retrieve, Update, and Delete API for Category
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ComponentViewSet(viewsets.ModelViewSet):
    serializer_class = ComponentSerializer

    def get_queryset(self):
        queryset = Component.objects.all()
        is_mtm = self.request.query_params.get('is_mtm', None)
        if is_mtm:
            is_mtm = is_mtm.lower() == 'true'  # Convert to boolean
            queryset = queryset.filter(is_mtm=is_mtm)
        return queryset 


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        queryset = Category.objects.all().order_by('category')
        categories_list = list(queryset.values())
        print("Categories being sent:", categories_list)  # Debug log
        return queryset


class SubCategoryListView(ListAPIView):
    serializer_class = SubCategorySerializer

    def get_queryset(self):
        category_name = self.request.query_params.get('category', None)
        if not category_name:
            return SubCategory.objects.none()

        # Print debug information
        print(f"Looking for subcategories with category name: {category_name}")
        queryset = SubCategory.objects.filter(category__category=category_name)
        print(f"Found subcategories: {list(queryset.values())}")
        return queryset

class TokenRefreshAPIView(APIView):
    def post(self, request):
        # Extract the refresh token from the request data
        refresh_token = request.data.get("refresh", None)

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create a RefreshToken object
            refresh = RefreshToken(refresh_token)
            
            # Generate access token from refresh token
            access_token = str(refresh.access_token)
            
            return Response({"access": access_token}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_return_status(request, requestId, itemId):
    """Update return status for a component"""
    try:
        # Get the component
        component = get_object_or_404(Component, id=itemId)
        
        # Validate input data
        serializer = ReturnStatusSerializer(data={
            **request.data,
            'request_id': requestId,
            'item_id': itemId
        })
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update component status
        new_status = serializer.validated_data['return_status']
        component.return_status = new_status
        component.returnable = new_status in ['DEFECTIVE', 'TO_BE_RETURNED']
        component.save()

        # Calculate stats
        stats = {
            'returnable': Component.objects.filter(
                return_status__in=['DEFECTIVE', 'TO_BE_RETURNED']
            ).count(),
            'defective': Component.objects.filter(
                return_status='DEFECTIVE'
            ).count()
        }

        return Response({
            'status': 'success',
            'item_id': itemId,
            'request_id': requestId,
            'new_status': new_status,
            'stats': stats
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error updating return status: {str(e)}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
class CategoryCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            print("Received category data:", request.data)  # Debug log
            
            if not request.data.get('category'):
                return Response(
                    {"error": "Category name is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            category_name = request.data.get('category').strip()
            if not category_name:
                return Response(
                    {"error": "Category name cannot be empty"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if category already exists
            if Category.objects.filter(category__iexact=category_name).exists():
                return Response(
                    {"error": "Category already exists"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = CategorySerializer(data={'category': category_name})
            if serializer.is_valid():
                category = serializer.save()
                response_data = CategorySerializer(category).data
                print("Created category:", response_data)  # Debug log
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            print("Serializer errors:", serializer.errors)  # Debug log
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print("Error in category creation:", str(e))  # Debug log
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class SubCategoryCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SubCategorySerializer(data=request.data)
        if serializer.is_valid():
            subcategory = serializer.save()
            return Response(SubCategorySerializer(subcategory).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)