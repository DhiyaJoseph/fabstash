from django.test import TestCase
import json
import os
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
# Add missing model imports
from .models import Category, SubCategory, Component  # Added SubCategory and Component imports

class PermissionTest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpass')
        self.normal_user = User.objects.create_user(username='user', password='userpass')
        self.category_list_url = '/api/categories/'
        self.category_create_url = '/api/categories/create/'

    def test_admin_can_create_category(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.post(self.category_create_url, {'name': 'Test Category'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_create_category(self):
        self.client.login(username='user', password='userpass')
        response = self.client.post(self.category_create_url, {'name': 'Test Category'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_view_categories(self):
        self.client.login(username='user', password='userpass')
        response = self.client.get(self.category_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create_category(self):
        response = self.client.post(self.category_create_url, {'name': 'Test Category'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)  
    
    def has_permission(self, request, view):
        # Check if the user is an admin or superadmin
        user = request.user
        if user.is_authenticated:
            return user.is_superuser or user.is_staff  # is_superuser (superadmin) or is_staff (admin)
        return False

class BackupJsonTestCase(TestCase):
    def setUp(self):
        backup_path = os.path.join(settings.BASE_DIR, 'backup.json')
        with open(backup_path, 'r') as f:
            self.backup_data = json.load(f)

    # Add missing test_category_data method
    def test_category_data(self):
        """Test if Category data can be loaded"""
        category_data = [item for item in self.backup_data if item['model'] == 'InventoryApp.category']
        for cat in category_data:
            Category.objects.create(
                id=cat['pk'],
                category=cat['fields']['category'],
                category_slug=cat['fields'].get('category_slug', '')
            )
        return True  # Return True so other tests can use this method

    def test_compare_model_fields(self):
        """Compare JSON data fields with model fields"""
        # Get all model entries from JSON
        json_categories = [item for item in self.backup_data if item['model'] == 'InventoryApp.category']
        json_subcategories = [item for item in self.backup_data if item['model'] == 'InventoryApp.subcategory']
        json_components = [item for item in self.backup_data if item['model'] == 'InventoryApp.component']

        # Print differences in fields
        print("\nCategory Fields Comparison:")
        json_category_fields = set(json_categories[0]['fields'].keys()) if json_categories else set()
        model_category_fields = {f.name for f in Category._meta.get_fields() 
                               if not f.is_relation and f.name != 'id'}  # Exclude id field
        print("Fields only in JSON:", json_category_fields - model_category_fields)
        print("Fields only in Model:", model_category_fields - json_category_fields)

        print("\nSubCategory Fields Comparison:")
        if json_subcategories:  # Add check to prevent empty list access
            json_subcategory_fields = set(json_subcategories[0]['fields'].keys())
            model_subcategory_fields = {f.name for f in SubCategory._meta.get_fields() 
                                      if not f.is_relation and f.name != 'id'}
            print("Fields only in JSON:", json_subcategory_fields - model_subcategory_fields)
            print("Fields only in Model:", model_subcategory_fields - json_subcategory_fields)
        else:
            print("No subcategories found in JSON")

        print("\nComponent Fields Comparison:")
        if json_components:  # Add check to prevent empty list access
            json_component_fields = set(json_components[0]['fields'].keys())
            model_component_fields = {f.name for f in Component._meta.get_fields() 
                                   if not f.is_relation and f.name != 'id'}
            print("Fields only in JSON:", json_component_fields - model_component_fields)
            print("Fields only in Model:", model_component_fields - json_component_fields)
        else:
            print("No components found in JSON")

    def test_data_values(self):
        """Compare actual values between JSON and database"""
        if not self.test_category_data():  # Call test_category_data and check return
            print("Failed to load category data")
            return
        
        # Compare category values
        for json_cat in [item for item in self.backup_data if item['model'] == 'InventoryApp.category']:
            try:
                db_cat = Category.objects.get(pk=json_cat['pk'])
                print(f"\nCategory {db_cat.id}:")
                for field, value in json_cat['fields'].items():
                    db_value = getattr(db_cat, field, None)
                    if db_value != value:
                        print(f"Field '{field}' differs - JSON: {value}, DB: {db_value}")
            except Category.DoesNotExist:
                print(f"Category with pk {json_cat['pk']} not found in database")

    def test_load_all_data(self):
        """Test loading all data from backup.json"""
        # Step 1: Load Categories
        categories = [item for item in self.backup_data if item['model'] == 'InventoryApp.category']
        for cat_data in categories:
            Category.objects.create(
                id=cat_data['pk'],
                category=cat_data['fields']['category'],
                category_slug=cat_data['fields'].get('category_slug', '')
            )
        
        # Step 2: Load SubCategories
        subcategories = [item for item in self.backup_data if item['model'] == 'InventoryApp.subcategory']
        for subcat_data in subcategories:
            SubCategory.objects.create(
                id=subcat_data['pk'],
                sub_category=subcat_data['fields']['sub_category'],
                category_id=subcat_data['fields']['category']
            )
        
        # Step 3: Load Components
        components = [item for item in self.backup_data if item['model'] == 'InventoryApp.component']
        for comp_data in components:
            fields = comp_data['fields']
            Component.objects.create(
                id=comp_data['pk'],
                name=fields['name'],
                category_id=fields.get('category'),
                sub_category_id=fields.get('sub_category'),
                quantity=fields.get('quantity', 0),
                comp_description=fields.get('comp_description', ''),
                component_location=fields.get('component_location', ''),
                package=fields.get('package', '')
            )
        
        # Verify the data
        self.assertEqual(Category.objects.count(), len(categories))
        self.assertEqual(SubCategory.objects.count(), len(subcategories))
        self.assertEqual(Component.objects.count(), len(components))

        # Print loaded data for verification
        print("\nLoaded Categories:")
        for cat in Category.objects.all():
            print(f"- {cat.category}")
            
        print("\nLoaded SubCategories:")
        for subcat in SubCategory.objects.all():
            print(f"- {subcat.sub_category} (Category: {subcat.category.category})")
            
        print("\nLoaded Components:")
        for comp in Component.objects.all():
            print(f"- {comp.name} (Category: {comp.category.category if comp.category else 'None'}, "
                  f"SubCategory: {comp.sub_category.sub_category if comp.sub_category else 'None'})")

