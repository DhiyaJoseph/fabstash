from django.shortcuts import render
from django.db.models import Q
from InventoryApp.models import Component
import json
from django.http import JsonResponse
from taggit.models import Tag
from django.core.exceptions import ObjectDoesNotExist
from InventoryConsumer.models import ConsumerSession, SessionComponents
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

# Create your views here.

def search_result(request):
    query = request.GET.get('q')
    # user_authenticated = request.user.is_authenticated
    search_result = Component.objects.all().filter(tags__name__in=[query], quantity__gt=0)
    session = ConsumerSession.objects.get(user=request.user)

    for component  in search_result:
        session_quantity = SessionComponents.objects.filter(session=session, component=component).values('component_quantity').first()
        component.session_quantity = session_quantity['component_quantity'] if session_quantity else None

    print(search_result)
    number = len(search_result)
    return render(request, 'searchresult.html', {'query': query, 'search_result': search_result, 'number': number})


def tag_autocomplete(request):
    if request.method == 'GET' and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        query = request.GET.get('query', '')
        tags = Tag.objects.filter(name__icontains=query).values_list('name', flat=True)[:10]
        data = {'tag-results': list(tags)}
        return JsonResponse(data, safe=False)
    return JsonResponse({'error':'invalid input'})



def search_components(request):
    try:
        q = request.GET.get('q', '').strip()
        if not q or len(q) < 2:
            return JsonResponse({'results': json.dumps([], cls=DecimalEncoder)}, safe=False)

        base_query = Component.objects.select_related('category', 'sub_category').prefetch_related('tags')
        
        filters = Q(name__icontains=q) | \
                 Q(category__category__icontains=q) | \
                 Q(sub_category__sub_category__icontains=q) | \
                 Q(component_location__icontains=q)

        if request.user.is_authenticated:
            filters |= Q(tags__name__icontains=q) | Q(comp_description__icontains=q)

        components = base_query.filter(filters, quantity__gt=0).distinct()[:15]

        # Get session quantities if user is authenticated
        session_quantity_dict = {}
        if request.user.is_authenticated:
            try:
                consumer_session = ConsumerSession.objects.get(user=request.user)
                session_components = SessionComponents.objects.filter(
                    session=consumer_session
                ).values('component_id', 'component_quantity')
                session_quantity_dict = {
                    item['component_id']: item['component_quantity'] 
                    for item in session_components
                }
            except ConsumerSession.DoesNotExist:
                pass

        # Safely get component attributes with fallbacks
        component_list = []
        for component in components:
            try:
                component_data = {
                    'id': component.id,
                    'name': component.name,
                    'comp_description': getattr(component, 'comp_description', '') or '',
                    'category': component.category.category if component.category else '',
                    'sub_category': component.sub_category.sub_category if component.sub_category else '',
                    'comp_image': component.comp_image.url if getattr(component, 'comp_image', None) else getattr(component, 'image_link', ''),
                    'quantity': int(component.quantity),  # Convert to int
                    'component_location': getattr(component, 'component_location', '') or '',
                    'tags': [tag.name for tag in component.tags.all()],
                    'session_quantity': int(session_quantity_dict.get(component.id, 0)),  # Convert to int
                    'package': getattr(component, 'package', '') or '',
                    'library': getattr(component, 'library', '') or '',
                    'datasheet': getattr(component, 'datasheet', '') or '',
                    'cost': float(getattr(component, 'cost', 0) or 0)  # Convert Decimal to float
                }
                
                if hasattr(component, 'returnable'):
                    component_data['returnable'] = bool(component.returnable)
                
                component_list.append(component_data)
            except Exception as e:
                logger.error(f"Error processing component {component.id}: {str(e)}")
                continue
        
        return JsonResponse(
            {'results': json.dumps(component_list, cls=DecimalEncoder)}, 
            safe=False
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Search failed',
            'details': str(e)
        }, status=500)
