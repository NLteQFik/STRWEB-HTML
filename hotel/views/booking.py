import logging
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import BookingForm
from ..models import Booking
from .auth import (
    apply_request_timezone,
    build_common_time_context,
    dual_timezone_display,
    is_client,
)

logger = logging.getLogger("hotel")


@login_required(login_url="login")
def booking_user_view(request):
    common_context = build_common_time_context(request)
    user_tz = ZoneInfo(common_context["user_timezone_name"])
    if not is_client(request.user):
        return render(
            request,
            "hotel/booking_user.html",
            {"form": None, "bookings": [], "booking_rows": [], **common_context},
        )
    profile = request.user.client_profile
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = Booking.objects.create(
                room=form.cleaned_data["room"],
                client=profile,
                check_in_date=form.cleaned_data["date_from"],
                check_out_date=form.cleaned_data["date_to"],
                total_cost=form.cleaned_data["room"].category.base_price,
                status=Booking.BookingStatus.ACTIVE,
            )
            booking.extra_services.set(form.cleaned_data["extra_services"])
            logger.info(
                "Booking created id=%s room=%s client=%s",
                booking.pk,
                booking.room.room_number,
                booking.client.full_name,
            )
            return redirect("booking_user")
        logger.warning("Booking form validation failed: %s", form.errors)
    else:
        form = BookingForm()
    bookings = Booking.objects.filter(client=profile).select_related("room", "room__category")
    booking_rows = [
        {
            "booking": booking,
            "created_times": dual_timezone_display(booking.created_at, user_tz),
            "updated_times": dual_timezone_display(booking.updated_at, user_tz),
        }
        for booking in bookings
    ]
    return render(
        request,
        "hotel/booking_user.html",
        {"form": form, "bookings": bookings, "booking_rows": booking_rows, **common_context},
    )


@login_required(login_url="login")
def booking_cancel_view(request, pk):
    apply_request_timezone(request)
    booking = get_object_or_404(Booking, pk=pk)
    if booking.client.user != request.user:
        return HttpResponseForbidden("Вы можете отменить только свое бронирование.")
    booking.status = Booking.BookingStatus.CANCELED
    booking.save(update_fields=["status", "updated_at"])
    return redirect("booking_user")
