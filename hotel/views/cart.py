import logging
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..cart import (
    add_to_cart,
    clear_cart,
    get_cart_items,
    remove_from_cart,
    set_cart_quantity,
)
from ..forms import CartPaymentForm
from ..models import Booking, Payment, Room
from .auth import build_common_time_context

logger = logging.getLogger("hotel")


def cart_view(request):
    cart_items, cart_total = get_cart_items(request)
    return render(
        request,
        "hotel/cart.html",
        {"cart_items": cart_items, "cart_total": cart_total, **build_common_time_context(request)},
    )


@require_POST
def cart_add_view(request, pk):
    room = get_object_or_404(Room, pk=pk)
    try:
        quantity = max(int(request.POST.get("quantity", 1)), 1)
    except (TypeError, ValueError):
        quantity = 1
    add_to_cart(request, room.pk, quantity)
    messages.success(request, f"Номер {room.room_number} добавлен в корзину.")
    return redirect(request.POST.get("next") or "cart_view")


@require_POST
def cart_remove_view(request, pk):
    remove_from_cart(request, pk)
    messages.success(request, "Позиция удалена из корзины.")
    return redirect("cart_view")


@require_POST
def cart_increase_view(request, pk):
    cart_items, _ = get_cart_items(request)
    current = next((i["quantity"] for i in cart_items if str(i["room"].pk) == str(pk)), 0)
    set_cart_quantity(request, pk, current + 1)
    return redirect("cart_view")


@require_POST
def cart_decrease_view(request, pk):
    cart_items, _ = get_cart_items(request)
    current = next((i["quantity"] for i in cart_items if str(i["room"].pk) == str(pk)), 0)
    set_cart_quantity(request, pk, current - 1)
    return redirect("cart_view")


@login_required(login_url="login")
def cart_payment_view(request):
    cart_items, cart_total = get_cart_items(request)
    if not cart_items:
        messages.warning(request, "Корзина пуста.")
        return redirect("cart_view")
    if not hasattr(request.user, "client_profile"):
        messages.error(request, "Оплата доступна только клиентам.")
        return redirect("cart_view")
    if request.method == "POST":
        form = CartPaymentForm(request.POST)
        if form.is_valid():
            client = request.user.client_profile
            created = 0
            for item in cart_items:
                room = item["room"]
                check_in = date.today() + timedelta(days=30 + int(room.pk))
                check_out = check_in + timedelta(days=max(item["quantity"], 1))
                booking = Booking.objects.create(
                    room=room,
                    client=client,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    total_cost=item["line_total"],
                    status=Booking.BookingStatus.ACTIVE,
                )
                Payment.objects.create(
                    booking=booking,
                    amount=item["line_total"],
                    status=Payment.PaymentStatus.PAID,
                )
                created += 1
            clear_cart(request)
            logger.info("Cart paid user=%s bookings=%s total=%s", request.user.pk, created, cart_total)
            messages.success(request, f"Оплата прошла успешно. Создано бронирований: {created}. Сумма: {cart_total} BYN.")
            return redirect("booking_user")
    else:
        form = CartPaymentForm()
    return render(
        request,
        "hotel/cart_payment.html",
        {"form": form, "cart_items": cart_items, "cart_total": cart_total, **build_common_time_context(request)},
    )
