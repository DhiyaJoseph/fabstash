from rest_framework import serializers
from rest_framework.decorators import api_view
from django.contrib.auth.models import User 
from django.contrib.auth import get_user_model
from .models import Component, Category, SubCategory
from .models import Invitation
from .models import UserProfile
from .models import Request, RequestItem


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    date_added = serializers.DateTimeField(source='date_joined', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'date_added', 'profile']
        depth = 1  # This will include the profile data in the response


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['id', 'email', 'role', 'token', 'is_accepted', 'created_at']


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category', read_only=True)
    
    class Meta:
        model = SubCategory
        fields = ['id', 'sub_category', 'category', 'category_name']

    def validate(self, data):
        if not data.get('category'):
            raise serializers.ValidationError({'category': 'Category is required'})
        return data

    def to_representation(self, instance):
        """Convert sub_category field to subcategory in response"""
        data = super().to_representation(instance)
        data['subcategory'] = data.pop('sub_category')
        return data

    def to_internal_value(self, data):
        """Convert subcategory field to sub_category for model"""
        if 'subcategory' in data:
            data['sub_category'] = data.pop('subcategory')
        return super().to_internal_value(data)


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(source='subcategory_set', many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'category', 'category_slug', 'subcategories']
        read_only_fields = ['category_slug', 'id']  # Make category_slug read-only

    def to_representation(self, instance):
        try:
            representation = super().to_representation(instance)
            # Remove null or empty subcategories
            if not representation.get('subcategories'):
                representation['subcategories'] = []
            return representation
        except Exception as e:
            print(f"Error serializing category {instance.id}: {str(e)}")
            return {
                'id': instance.id,
                'category': instance.category,
                'category_slug': instance.category_slug,
                'subcategories': []
            }

    def create(self, validated_data):
        print("Creating category with data:", validated_data)  # Debug log
        try:
            return Category.objects.create(**validated_data)
        except Exception as e:
            print("Error creating category:", str(e))  # Debug log
            raise


class ComponentSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    sub_category = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.category', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.sub_category', read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            'id', 'name', 'category', 'category_name', 
            'sub_category', 'sub_category_name',
            'quantity', 'comp_description', 'component_location',
            'package', 'is_mtm', 'returnable','cost',
            'min_quantity', 'request_count', 'image_option',
            'image_link', 'return_status', 'datasheet', 'library',
            'tags', 'price'  # Added price field
        ]

    def get_category(self, obj):
        if obj.category:
            return {
                'id': obj.category.id,
                'category': obj.category.category,
                'category_slug': obj.category.category_slug
            }
        return None

    def get_sub_category(self, obj):
        if obj.sub_category:
            return {
                'id': obj.sub_category.id,
                'sub_category': obj.sub_category.sub_category,
                'sub_category_slug': obj.sub_category.sub_category_slug
            }
        return None

    def get_tags(self, obj):
        try:
            return [tag.name for tag in obj.tags.all()]
        except Exception:
            return []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure these fields are never null
        data['datasheet'] = data.get('datasheet') or ''
        data['library'] = data.get('library') or ''
        data['package'] = data.get('package') or ''
        data['category'] = data.get('category') or {}
        data['sub_category'] = data.get('sub_category') or {}
        return data


class ReturnStatusSerializer(serializers.Serializer):
    return_status = serializers.ChoiceField(choices=[
        ('RETURNED', 'Returned'),
        ('DEFECTIVE', 'Defective'),
        ('TO_BE_RETURNED', 'To be Returned'),
    ])
    request_id = serializers.IntegerField()
    item_id = serializers.IntegerField()

    def update(self, instance, validated_data):
        instance.return_status = validated_data.get('return_status', instance.return_status)
        instance.save()
        return instance


class RequestItemSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)

    class Meta:
        model = RequestItem
        fields = ['id', 'component_name', 'quantity', 'status', 'location', 'existing_quantity']


class RequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    component_name = serializers.CharField(source='component.name')
    component_location = serializers.CharField(source='component.component_location')
    created_at_formatted = serializers.DateTimeField(
        source='created_at', 
        format="%Y-%m-%d %H:%M:%S"
    )

    class Meta:
        model = Request
        fields = [
            'id', 'username', 'component_name', 'component_location',
            'quantity', 'status', 'return_status', 'created_at_formatted'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add any computed fields or transform data if needed
        return data


