from rest_framework import serializers
from .models import ConsumerSession, SessionComponents
from InventoryApp.models import Component, Category, SubCategory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'category']

class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'sub_category']

class ComponentSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    sub_category = SubCategorySerializer()

    class Meta:
        model = Component
        fields = ['id', 'name', 'category', 'sub_category', 'comp_image', 'component_location']

class SessionComponentSerializer(serializers.ModelSerializer):
    component = ComponentSerializer()
    
    class Meta:
        model = SessionComponents
        fields = ['id', 'component', 'component_quantity']

class AddSessionComponentSerializer(serializers.Serializer):
    component_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)