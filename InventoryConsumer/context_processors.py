from InventoryConsumer.models import ConsumerSession, SessionComponents

def count_items(request):
    item_count = 0
    if 'admin' in request.path:
        return {}
    try:
        session = ConsumerSession.objects.get(user=request.user.id)
        components = SessionComponents.objects.filter(session=session)
        for component in components:
            item_count += component.component_quantity
        return {'item_count': item_count}
    except ConsumerSession.DoesNotExist:
        item_count = 0

        return {'item_count': item_count}
    