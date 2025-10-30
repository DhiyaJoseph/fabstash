from typing import Any
from django import forms
from InventoryApp.models import Component
from taggit.forms import TagWidget

class ComponentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ComponentForm, self).__init__(*args, **kwargs)
        self.fields['image_option'].initial = 'link'

    class Meta:
        model = Component
        fields = [
            'category',
            'sub_category', 
            'name', 
            'comp_description', 
            'tags', 
            'component_location', 
            'comp_image', 
            'quantity',
            'image_option',
            'datasheet',
            'image_link',
            'library',
            'package',
            'is_mtm',
            'is_returnable',  # Make sure this matches exactly with the model field name
            'cost',
            'min_quantity',
            'price'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control text-dark'}),
            'comp_description': forms.Textarea(attrs={'class': 'form-control text-dark', 'style': 'height: 203px'}),
            'component_location': forms.TextInput(attrs={'class': 'form-control text-dark', 'maxlength': '12'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control text-dark'}),   
            'comp_image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control text-dark select2'}),
            'sub_category': forms.Select(attrs={'class': 'form-control text-dark select2'}),
            'tags': TagWidget(attrs={'class': 'form-control text-dark ', 'style': 'height: 37px'}),
            'image_option': forms.Select(attrs={'class': 'form-control text-dark', 'id': 'image_option'}),
            'datasheet': forms.URLInput(attrs={'class': 'form-control text-dark', 'placeholder': 'https://'}),
            'image_link': forms.URLInput(attrs={'class': 'form-control text-dark', 'placeholder': 'https://'}),
            'library': forms.URLInput(attrs={'class': 'form-control text-dark', 'placeholder': 'https://'}),
            'package': forms.TextInput(attrs={'class': 'form-control text-dark'}),
            'is_mtm': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_returnable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # Update widget name too
            'cost': forms.NumberInput(attrs={'class': 'form-control text-dark'})
        }

    class Media:
        js = ('js/dependentdropdown.js',)
