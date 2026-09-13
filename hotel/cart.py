from decimal import Decimal

from .models import Room

CART_SESSION_KEY = "cart"


def get_cart(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(cart, dict):
        return {}
    cleaned = {}
    for room_id, quantity in cart.items():
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            cleaned[str(room_id)] = qty
    return cleaned


def save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def get_cart_item_count(request):
    return sum(get_cart(request).values())


def add_to_cart(request, room_id, quantity=1):
    cart = get_cart(request)
    key = str(room_id)
    cart[key] = cart.get(key, 0) + max(int(quantity), 1)
    save_cart(request, cart)


def set_cart_quantity(request, room_id, quantity):
    cart = get_cart(request)
    key = str(room_id)
    if int(quantity) <= 0:
        cart.pop(key, None)
    else:
        cart[key] = int(quantity)
    save_cart(request, cart)


def remove_from_cart(request, room_id):
    cart = get_cart(request)
    cart.pop(str(room_id), None)
    save_cart(request, cart)


def clear_cart(request):
    request.session[CART_SESSION_KEY] = {}
    request.session.modified = True


def get_cart_items(request):
    cart = get_cart(request)
    if not cart:
        return [], Decimal("0")
    rooms = Room.objects.filter(pk__in=[int(pk) for pk in cart.keys()]).select_related("category")
    rooms_map = {str(room.pk): room for room in rooms}
    items = []
    total = Decimal("0")
    for room_id, quantity in cart.items():
        room = rooms_map.get(room_id)
        if not room:
            continue
        line_total = room.category.base_price * quantity
        items.append({"room": room, "quantity": quantity, "line_total": line_total})
        total += line_total
    items.sort(key=lambda item: item["room"].room_number)
    return items, total
