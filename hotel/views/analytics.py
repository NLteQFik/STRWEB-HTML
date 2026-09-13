import statistics
from base64 import b64encode
from datetime import timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import matplotlib
import matplotlib.pyplot as plt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from ..models import Booking, Client, RoomCategory
from .auth import build_common_time_context, dual_timezone_display, get_age

matplotlib.use("Agg")


@login_required(login_url="login")
def hotel_analytics_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ только для суперпользователя.")
    common_context = build_common_time_context(request)
    user_tz = ZoneInfo(common_context["user_timezone_name"])
    today_local = timezone.now().astimezone(user_tz).date()

    bookings = Booking.objects.select_related(
        "room", "room__category", "client"
    ).prefetch_related("payments")
    booking_amounts = [float(booking.total_cost) for booking in bookings]

    total_revenue = sum(booking_amounts)
    average_check = statistics.mean(booking_amounts) if booking_amounts else 0
    mode_check = statistics.multimode(booking_amounts)
    median_check = statistics.median(booking_amounts) if booking_amounts else 0

    clients = Client.objects.all().order_by("full_name")
    client_ages = [get_age(client.birth_date, today_local) for client in clients]
    average_age = statistics.mean(client_ages) if client_ages else 0
    median_age = statistics.median(client_ages) if client_ages else 0

    popular_category = (
        Booking.objects.values("room__category__name")
        .annotate(total_count=Count("id"))
        .order_by("-total_count")
        .first()
    )
    profitable_category = (
        RoomCategory.objects.values("name")
        .annotate(total_revenue=Sum("rooms__bookings__payments__amount"))
        .order_by("-total_revenue")
        .first()
    )

    revenue_by_clients = (
        Client.objects.values("full_name")
        .annotate(total_sum=Sum("bookings__total_cost"))
        .order_by("full_name")
    )

    three_months_ago = today_local.replace(day=1) - timedelta(days=90)
    month_booking_stats = (
        Booking.objects.filter(updated_at__gte=three_months_ago)
        .annotate(month=TruncMonth("updated_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    chart_dates = [item["month"].strftime("%m/%Y") for item in month_booking_stats]
    chart_values = [item["total"] for item in month_booking_stats]
    if not chart_dates:
        chart_dates = [today_local.strftime("%m/%Y")]
        chart_values = [0]

    plt.figure(figsize=(9, 4))
    plt.bar(chart_dates, chart_values, color="skyblue")
    plt.title("Количество бронирований по месяцам (последние 3 месяца)")
    plt.xlabel("Дата")
    plt.ylabel("Бронирований")
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    chart_base64 = b64encode(buffer.read()).decode("ascii")

    context = {
        "total_revenue": total_revenue,
        "average_check": average_check,
        "mode_check": mode_check,
        "median_check": median_check,
        "average_age": average_age,
        "median_age": median_age,
        "popular_category_name": (
            popular_category["room__category__name"] if popular_category else "Нет данных"
        ),
        "profitable_category_name": (
            profitable_category["name"] if profitable_category else "Нет данных"
        ),
        "revenue_by_clients": revenue_by_clients,
        "booking_rows": [
            {
                "booking": booking,
                "created_times": dual_timezone_display(booking.created_at, user_tz),
                "updated_times": dual_timezone_display(booking.updated_at, user_tz),
            }
            for booking in bookings
        ],
        "clients": clients,
        "chart_base64": chart_base64,
        **common_context,
    }
    return render(request, "hotel/hotel_analytics.html", context)
