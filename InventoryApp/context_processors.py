from .models import Category, SubCategory

def category_links(request):
    links = Category.objects.all()
    return dict(category_links=links)
    

def subcategory_links(request):
    links = SubCategory.objects.all()
    return dict(subcategory_links=links)