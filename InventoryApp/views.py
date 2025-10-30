from django.shortcuts import render, redirect, get_object_or_404
from InventoryApp.models import  Component
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from InventoryConsumer.models import ConsumerSession, SessionComponents
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Component,Category, SubCategory
from .serializers import ComponentSerializer,CategorySerializer, SubCategorySerializer, ComponentSerializer,InvitationSerializer,UserSerializer
from rest_framework import status,viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .models import UserProfile
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Invitation
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from datetime import datetime, timezone
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.core.mail import send_mail
import uuid
from .models import UserProfile, UserInvitation
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail, BadHeaderError
from smtplib import SMTPException
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.db.models import Count, Q  # Add Q to imports


class SendInvitationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            print("User:", request.user)
            print("User role:", request.user.profile.role if hasattr(request.user, 'profile') else 'No profile')
            
            email = request.data.get('email')
            role = request.data.get('role')
            
            if not email or not role:
                return Response(
                    {"error": "Email and role are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create invitation with token
            token = str(uuid.uuid4())
            invitation = Invitation.objects.create(
                email=email,
                role=role,
                token=token
            )

            # Prepare email
            accept_url = f"http://localhost:5173/register/{token}"
            subject = "Invitation to Join Fab Inventory"

            # HTML version of the email
            html_message = f"""
            <html>
                <head>
                    <style>
                        .button {{
                            background-color: #4CAF50;
                            border: none;
                            color: white;
                            padding: 15px 32px;
                            text-align: center;
                            text-decoration: none;
                            display: inline-block;
                            font-size: 16px;
                            margin: 4px 2px;
                            cursor: pointer;
                            border-radius: 4px;
                        }}
                    </style>
                </head>
                <body>
                    <h2>Welcome to Fab Inventory!</h2>
                    <p>You have been invited to join Fab Inventory as a {role}.</p>
                    <p>Click the button below to accept the invitation and create your account:</p>
                    <a href="{accept_url}" class="button">Accept Invitation</a>
                    <p>This invitation will expire in 24 hours.</p>
                    
                    <br>
                    <p>Best regards,<br>Fab Inventory Team</p>
                </body>
            </html>
            """

            # Plain text version
            plain_message = f"""
            Welcome to Fab Inventory!
            
            You have been invited to join Fab Inventory as a {role}.
            
            Copy and paste this URL into your browser to accept the invitation:
            {accept_url}
            
            This invitation will expire in 24 hours.
            
            Best regards,
            Fab Inventory Team
            """

            try:
                print(f"Attempting to send email to {email} from {settings.EMAIL_HOST_USER}")
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                print("Email sent successfully")
                return Response(
                    {"message": "Invitation sent successfully."}, 
                    status=status.HTTP_201_CREATED
                )
                
            except BadHeaderError as e:
                print(f"BadHeaderError: {str(e)}")
                invitation.delete()
                return Response(
                    {"error": "Invalid email header"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            except SMTPException as e:
                print(f"SMTPException: {str(e)}")
                invitation.delete()
                return Response(
                    {"error": f"Failed to send email: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as e:
                print(f"Unexpected error sending email: {str(e)}")
                invitation.delete()
                return Response(
                    {"error": f"Failed to send email: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            print(f"Error in SendInvitationView: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AcceptInvitationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, token):
        try:
            with transaction.atomic():
                # Get invitation
                invitation = get_object_or_404(Invitation, token=token, is_accepted=False)
                
                # Check expiration
                if timezone.now() > invitation.created_at + timedelta(hours=24):
                    invitation.delete()
                    return Response(
                        {"error": "This invitation has expired"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Validate input
                username = request.data.get('username')
                password = request.data.get('password')

                if not username or not password:
                    return Response(
                        {"error": "Username and password are required"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check existing username
                if User.objects.filter(username=username).exists():
                    return Response(
                        {"error": "Username already taken"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create user first
                user = None
                try:
                    user = User.objects.create_user(
                        username=username,
                        email=invitation.email,
                        password=password
                    )
                    
                    # Create profile immediately after user
                    UserProfile.objects.create(
                        user=user,
                        role=invitation.role,
                        invitation_accepted=True
                    )

                    # Mark invitation as accepted
                    invitation.is_accepted = True
                    invitation.save()

                    # Generate tokens
                    refresh = RefreshToken.for_user(user)

                    return Response({
                        "message": "Account created successfully",
                        "username": username,
                        "role": invitation.role,
                        "access": str(refresh.access_token),
                        "refresh": str(refresh)
                    }, status=status.HTTP_201_CREATED)

                except Exception as e:
                    # If anything fails, make sure to clean up
                    if user:
                        user.delete()
                    raise e

        except IntegrityError as e:
            return Response(
                {"error": f"Database error: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error creating account: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
@api_view(['GET'])
def accept_invitation(request, token):
    """Validate invitation token and fetch invitation details."""
    if not token:
        return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        invitation = Invitation.objects.get(token=token, is_accepted=False)
        return Response({
            "message": "Invitation valid",
            "email": invitation.email
        }, status=status.HTTP_200_OK)
    except Invitation.DoesNotExist:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

class VerifyInvitationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            invitation = get_object_or_404(Invitation, token=token, is_accepted=False)
            
            # Check if invitation is expired (24 hours)
            if timezone.now() > invitation.created_at + timedelta(hours=24):
                invitation.delete()
                return Response(
                    {"error": "This invitation has expired", "valid": False}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                "email": invitation.email,
                "role": invitation.role,
                "valid": True
            }, status=status.HTTP_200_OK)
            
        except Invitation.DoesNotExist:
            return Response(
                {"error": "Invalid invitation token", "valid": False},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e), "valid": False}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        try:
            return User.objects.all().select_related('profile')
        except Exception as e:
            print(f"Error in get_queryset: {str(e)}")
            return User.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in list method: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class LoginView(APIView):
    permission_classes = []  # Allow unauthenticated access

    def post(self, request):
        try:
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')

            if not (username or email) or not password:
                return Response({
                    'error': 'Please provide a username or email and password'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Try to authenticate with username or email
            user = None
            if username:
                user = authenticate(username=username, password=password)
            elif email:
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass  # User will remain None

            if not user:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Determine user role
            role = 'User'
            is_staff = user.is_staff
            is_superuser = user.is_superuser

            if user.is_superuser:
                role = 'SuperAdmin'
            elif user.is_staff:
                role = 'Admin'

            # Ensure "superadmin" username is correctly set as superuser
            if user.username == 'superadmin' and not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                role = 'SuperAdmin'
                is_staff = True
                is_superuser = True

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh['role'] = role
            refresh['is_staff'] = is_staff
            refresh['is_superuser'] = is_superuser

            return Response({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': role,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ComponentListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            category_param = request.query_params.get('category')
            subcategory_param = request.query_params.get('subcategory')
            components = Component.objects.all()  # initial queryset

            if category_param:
                print("Category param:", category_param)
                components = components.filter(category__category_slug=category_param.lower())
            
            if subcategory_param:
                print("Subcategory param:", subcategory_param)
                components = components.filter(sub_category__sub_category_slug=subcategory_param.lower())

            serializer = ComponentSerializer(components, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# List and create categories
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

# Retrieve, Update, and Delete API for Category
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.all().order_by('category')

    def list(self, request, *args, **kwargs):
        category_id = request.query_params.get('category_id')

        if category_id:
            try:
                components = Component.objects.filter(category__id=category_id).order_by('name')
                serializer = ComponentSerializer(components, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": f"Failed to fetch components for category: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SubCategoryListView(generics.ListAPIView):
    serializer_class = SubCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = SubCategory.objects.all()
        category_id = self.request.query_params.get('category_id')
        sub_category_id = self.request.query_params.get('sub_category_id') 
        
        if category_id:
            queryset = queryset.filter(category__id=category_id)
        if sub_category_id:
            queryset = queryset.filter(id=sub_category_id)
        
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        sub_category_id = request.query_params.get('sub_category_id')  

        if sub_category_id:
            try:
                components = Component.objects.filter(sub_category__id=sub_category_id).order_by('name')  
                serializer = ComponentSerializer(components, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": f"Failed to fetch components for subcategory: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        queryset = self.get_queryset()
        if not queryset.exists():
            return Response([], status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IsAdminOrSuperAdmin(BasePermission):
    """
    Custom permission to allow only superadmin or admin to create categories.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow only if the user is a superadmin or admin
        return request.user.is_superuser or request.user.is_staff


class CategoryCreateView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]  # Apply custom permissions
    
    def create(self, request, *args, **kwargs):
        category_name = request.data.get('category')
        if not category_name:
            return Response(
                {'error': 'Category name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Case-insensitive check for existing category
            if Category.objects.filter(category__iexact=category_name.strip()).exists():
                # If category exists, return it instead of error
                existing_category = Category.objects.get(category__iexact=category_name.strip())
                serializer = self.get_serializer(existing_category)
                return Response(
                    serializer.data, 
                    status=status.HTTP_200_OK
                )

            # Create new category if it doesn't exist
            category = Category.objects.create(category=category_name.strip())
            serializer = self.get_serializer(category)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class SubCategoryCreateView(generics.CreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def create(self, request, *args, **kwargs):
        print("Received data:", request.data)  # Debug log
        
        subcategory_name = request.data.get('subcategory')
        category_id = request.data.get('category')

        if not subcategory_name:
            return Response(
                {'error': 'Subcategory name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not category_id:
            return Response(
                {'error': 'Category ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get category
            category = Category.objects.get(id=category_id)
            
            # Create subcategory data
            data = {
                'sub_category': subcategory_name.strip(),
                'category': category.id
            }
            
            # Save using serializer
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                # Save and return with transformed response
                instance = serializer.save()
                response_data = {
                    'id': instance.id,
                    'subcategory': instance.sub_category,
                    'category': instance.category.id,
                    'category_name': instance.category.category
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Category.DoesNotExist:
            return Response(
                {'error': f'Category with id {category_id} does not exist'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"Error creating subcategory: {str(e)}")  # Debug log
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

# Create your views here.
def all_components(request, category_slug=None, subcategory_slug=None):
    try:
        session = ConsumerSession.objects.get(user=request.user.id)
        session_components = SessionComponents.objects.filter(session=session)
    except ConsumerSession.DoesNotExist:
        session_components = None

    # Common filtering logic
    base_filter = Component.objects.filter(quantity__gt=0)

    # Conditional assignment using a ternary operator
    components = base_filter.order_by('id') if request.user.is_authenticated else base_filter.filter(is_mtm=False).order_by('id')

    if category_slug:
        components = components.filter(category__category_slug=category_slug)
    if subcategory_slug:
        components = components.filter(sub_category__sub_category_slug=subcategory_slug)

    paginator = Paginator(components, 15)
    page = request.GET.get('page', 1)
    component_list = paginator.get_page(page)

    if session_components is not None:
        for component in component_list:
            session_component = session_components.filter(component=component).first()
            if session_component:
                component.session_quantity = session_component.component_quantity

    context = {'components': component_list}
    return render(request, 'index.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_user(request):
    if request.user.userprofile.role not in ['Superadmin', 'Admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    email = request.data.get('email')
    role = request.data.get('role')
    
    if role == 'Superadmin' and request.user.userprofile.role != 'Superadmin':
        return Response({'error': 'Only Superadmin can invite other Superadmins'}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    token = str(uuid.uuid4())
    
    # Create invitation
    UserInvitation.objects.create(
        email=email,
        token=token,
        role=role,
        invited_by=request.user
    )
    return Response({'message': 'Invitation sent successfully'})

@api_view(['POST'])
def accept_invitation(request):
    token = request.data.get('token')
    password = request.data.get('password')
    
    try:
        invitation = UserInvitation.objects.get(token=token, accepted=False)
        
        # Create user and profile
        user = User.objects.create_user(
            username=invitation.email,
            email=invitation.email,
            password=password
        )
        
        UserProfile.objects.create(
            user=user,
            role=invitation.role,
            invitation_accepted=True
        )
        
        invitation.accepted = True
        invitation.save()
        
        return Response({'message': 'Account created successfully'})
        
    except UserInvitation.DoesNotExist:
        return Response({'error': 'Invalid or expired invitation'}, 
                      status=status.HTTP_400_BAD_REQUEST)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Component
from django.shortcuts import get_object_or_404

@api_view(['POST'])
def add_to_cart(request):
    component_id = request.data.get('component_id')
    quantity = request.data.get('quantity', 1)
    
    component = get_object_or_404(Component, id=component_id)
    
    # Check if requested quantity is available
    if component.quantity < quantity:
        return Response({
            'error': 'Insufficient quantity available',
            'available': component.quantity
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # If we have sufficient quantity, proceed with adding to cart
    try:
        # Your existing cart addition logic here
        component.quantity -= quantity  # Reduce available quantity
        component.save()
        
        return Response({
            'message': 'Added to cart successfully',
            'remaining_quantity': component.quantity
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def remove_from_cart(request):
    component_id = request.data.get('component_id')
    quantity = request.data.get('quantity', 1)
    
    component = get_object_or_404(Component, id=component_id)
    
    try:
        # Your existing cart removal logic here
        component.quantity += quantity  # Return quantity back to available stock
        component.save()
        
        return Response({
            'message': 'Removed from cart successfully',
            'available_quantity': component.quantity
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_component_quantity(request, component_id):
    component = get_object_or_404(Component, id=component_id)
    return Response({
        'quantity': component.quantity,
        'id': component.id
    })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])  # Allow public access
def frequent_components(request):
    try:
        # Get top 5 most requested components
        components = Component.objects.filter(
            quantity__gt=0  # Only show available components
        ).order_by('-request_count')[:5]
        
        serializer = ComponentSerializer(components, many=True)
        return Response(serializer.data)
    except Exception as e:
        print(f"Error in frequent_components: {str(e)}")  # Debug print
        return Response(
            {"error": "Internal server error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def track_component_request(request, component_id):
    try:
        component = Component.objects.get(id=component_id)
        component.request_count += 1
        component.save()
        return Response({"status": "success"})
    except Component.DoesNotExist:
        return Response(
            {"error": "Component not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def components_by_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    components = Component.objects.filter(category=category, quantity__gt=0).order_by('-id')
    
    paginator = Paginator(components, 12)  # Show 12 components per page
    page = request.GET.get('page', 1)
    
    try:
        components_list = paginator.page(page)
    except:
        components_list = paginator.page(1)
        
    return render(request, 'App/components.html', {
        'components': components_list,
        'selected_category': category
    })

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class UserDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        try:
            # Use get_or_create to ensure a profile exists
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'NormalUser'}
            )
            
            data = {
                'username': user.username,
                'email': user.email,
                'role': profile.role,
                'date_joined': user.date_joined,
            }
            return Response(data)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.parsers import JSONParser

class ComponentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    parser_classes = [JSONParser]  # Use JSONParser for JSON requests
    

    def post(self, request, *args, **kwargs):
        try:
            data = request.data  # No need to call dict() on request.data when using JSONParser
            print("Received raw data:", data)  # Debug log

            # Extract category and subcategory
            category_id = data.get('category')
            sub_category_id = data.get('sub_category')

            try:
                category = Category.objects.get(id=category_id)
                sub_category = SubCategory.objects.get(id=sub_category_id)

                # Create component data with all required fields
                component_data = {
                    'name': data.get('name'),
                    'comp_description': data.get('comp_description'),
                    'quantity': int(data.get('quantity', 0)),
                    'min_quantity': int(data.get('min_quantity', 0)),
                    'cost': float(data.get('cost', 0.0)),
                    'component_location': data.get('component_location'),
                    'package': data.get('package', ''),
                    'is_mtm': str(data.get('is_mtm')).lower() == 'true',
                    'is_returnable': str(data.get('is_returnable', 'false')).lower() == 'true',
                    'category': category,
                    'sub_category': sub_category,
                }

                if 'comp_image' in request.FILES:
                    component_data['comp_image'] = request.FILES['comp_image']

                print("Component data before creation:", component_data)  # Debug log

                # Create component
                component = Component.objects.create(**component_data)
                return Response(
                    ComponentSerializer(component).data,
                    status=status.HTTP_201_CREATED
                )

            except (Category.DoesNotExist, SubCategory.DoesNotExist) as e:
                return Response(
                    {"error": f"Invalid category or subcategory: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                print(f"Error creating component: {str(e)}")  # Debug log
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            print(f"Error in view: {str(e)}")  # Debug log
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_details(request):
    user = request.user
    try:
        profile = user.profile  # Get associated UserProfile
        return Response({
            'username': user.username,
            'email': user.email,
            'role': profile.role,
            'date_joined': user.date_joined,
            'is_active': user.is_active
        })
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
class ComponentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, pk):
        try:
            return Component.objects.get(pk=pk)
        except Component.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        component = self.get_object(pk)
        serializer = ComponentSerializer(component)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        try:
            component = self.get_object(pk)
            serializer = ComponentSerializer(component, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        component = self.get_object(pk)
        component.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_components(request):
    try:
        # Get the 5 most recently added components by ordering by ID in descending order
        recent = Component.objects.all().order_by('-id')[:5]
        
        serializer = ComponentSerializer(recent, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error in recent_components: {str(e)}")
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def test_email(request):
    """Test email functionality"""
    try:
        recipient = request.data.get('email', settings.EMAIL_HOST_USER)
        
        # Send test email
        send_mail(
            subject='Test Email from Fab Inventory',
            message='This is a test email to verify the email configuration is working.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        print(f"Test email sent successfully to {recipient}")
        return Response({
            "message": "Test email sent successfully",
            "recipient": recipient
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error sending test email: {str(e)}")
        return Response({
            "error": f"Failed to send test email: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.shortcuts import get_object_or_404
from .models import Category, SubCategory

# In your component creation view
def create_component(request):
    try:
        data = request.POST
        category_id = data.get('category')
        subcategory_id = data.get('sub_category')

        # Get category and subcategory instances
        category = get_object_or_404(Category, id=category_id) if category_id else None
        subcategory = get_object_or_404(SubCategory, id=subcategory_id) if subcategory_id else None

        component = Component.objects.create(
            category=category,
            sub_category=subcategory,
            # ... rest of your fields ...
        )
        
        return JsonResponse({'message': 'Component created successfully', 'id': component.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stock_status(request):
    try:
        # Get all components
        components = Component.objects.all()
        
        # Filter out of stock and low stock components
        out_of_stock = components.filter(quantity=0)
        low_stock = components.filter(quantity__gt=0, quantity__lte=models.F('min_quantity'))
        
        # Serialize the data
        out_of_stock_data = ComponentSerializer(out_of_stock, many=True).data
        low_stock_data = ComponentSerializer(low_stock, many=True).data
        
        return Response({
            'out_of_stock': out_of_stock_data,
            'low_stock': low_stock_data,
            'total_out_of_stock': out_of_stock.count(),
            'total_low_stock': low_stock.count()
        })
    except Exception as e:
        print(f"Error in get_stock_status: {str(e)}")
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Component

@api_view(['PATCH'])
def update_return_status(request, component_id):
    try:
        component = Component.objects.get(id=component_id)
    except Component.DoesNotExist:
        return Response({'error': 'Component not found'}, status=404)

    new_status = request.data.get('return_status')

    if new_status not in ['Returned', 'Defective', 'To be Returned']:
        return Response({'error': 'Invalid return status'}, status=400)

    component.update_return_status(new_status)
    return Response({'message': 'Status updated successfully'}, status=200)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count
from .models import Request

@api_view(['GET'])
def user_request_stats(request):
    try:
        # Get request statistics using is_returnable instead of returnable
        stats = Request.objects.filter(user=request.user).select_related('component').aggregate(
            total_requests=Count('id'),
            pending_requests=Count('id', filter=models.Q(status='PENDING')),
            returnable_items=Count('id', filter=models.Q(component__is_returnable=True))
        )
        return Response(stats)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

def debug_components(request):
    """Temporary debug view to check component data"""
    components = list(Component.objects.values())
    return JsonResponse({
        'count': len(components),
        'components': components
    })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Request
from .serializers import RequestSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_log(request):
    try:
        requests = Request.objects.filter(user=request.user).select_related('user', 'component')
        print(f"Found {requests.count()} requests")  # Debug log
        
        serializer = RequestSerializer(requests, many=True)
        print("Serialized data:", serializer.data)  # Debug log
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': requests.count()
        })
    except Exception as e:
        print(f"Error in request_log: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'data': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_request(request):
    try:
        print("Received request data:", request.data)  # Debug log
        items = request.data.get('items', [])
        
        if not items:
            return Response({'error': 'No items provided'}, status=400)
            
        created_requests = []
        
        with transaction.atomic():
            for item in items:
                component = Component.objects.get(id=item['component_id'])
                request_obj = Request.objects.create(
                    user=request.user,
                    component=component,
                    quantity=item['quantity'],
                    status='PENDING',
                    created_at=timezone.now()  # Explicitly set creation time
                )
                print(f"Created request: {request_obj.id}")  # Debug log
                created_requests.append(request_obj)

            # Clear the user's cart after successful creation
            try:
                ConsumerSession.objects.filter(user=request.user).delete()
            except Exception as e:
                print(f"Error clearing cart: {e}")

            # Serialize the created requests
            serializer = RequestSerializer(created_requests, many=True)
            
            return Response({
                'message': 'Requests submitted successfully',
                'count': len(created_requests),
                'requests': serializer.data  # Include the actual request data
            }, status=201)
            
    except Exception as e:
        print(f"Error in submit_request: {str(e)}")
        return Response({'error': str(e)}, status=500)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_requests(request):
    try:
        # Query requests with related data
        queryset = Request.objects.filter(
            user=request.user
        ).select_related(
            'component', 'user'
        ).order_by('-created_at')

        print(f"Found {queryset.count()} requests for user {request.user.username}")

        # Include full request details in serialization
        serializer = RequestSerializer(queryset, many=True)
        
        # Debug log serialized data
        print("Serialized request data:", serializer.data)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queryset.count()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in list_requests: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'data': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_manager_requests(request):
    try:
        requests = Request.objects.all().select_related(
            'user', 'component'
        ).order_by('-created_at')

        serializer = RequestSerializer(requests, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': requests.count()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'data': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_request_status(request, request_id):
    """Update request status"""
    try:
        with transaction.atomic():  # Add transaction to ensure data consistency
            req = Request.objects.get(id=request_id)
            new_status = request.data.get('status', '').upper()
            
            # Validate status
            valid_statuses = ['PENDING', 'APPROVED', 'REJECTED']
            if new_status not in valid_statuses:
                return Response({
                    'error': f'Invalid status. Must be one of {valid_statuses}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update main request status
            req.status = new_status
            req.save()

            # Update all related items status
            RequestItem.objects.filter(request=req).update(status=new_status)

            # Get updated stats
            stats = Request.objects.aggregate(
                pending=Count('id', filter=Q(status='PENDING')),
                approved=Count('id', filter=Q(status='APPROVED')),
                rejected=Count('id', filter=Q(status='REJECTED')),
                returnable=Count('id', filter=Q(component__is_returnable=True))
            )
            
            return Response({
                'success': True,
                'request_status': new_status,
                'stats': stats,
                'request': {
                    'id': req.id,
                    'status': new_status,
                    'username': req.user.username,
                    'component_name': req.component.name,
                    'quantity': req.quantity,
                    'date': req.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
            
    except Request.DoesNotExist:
        return Response({
            'error': 'Request not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error updating status: {str(e)}")  # Add debug print
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_request_stats(request):
    """Get current request statistics"""
    try:
        stats = Request.objects.aggregate(
            pending=Count('id', filter=Q(status='PENDING')),
            approved=Count('id', filter=Q(status='APPROVED')),
            rejected=Count('id', filter=Q(status='REJECTED')),
            returnable=Count('id', filter=Q(component__is_returnable=True))
        )
        return Response(stats)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)