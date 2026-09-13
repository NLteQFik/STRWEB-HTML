import logging
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from ..forms import CompanyInfoForm
from ..models import Article, CompanyInfo, RoomCategory, Room
from ..services import get_external_data, get_weather_data
from .auth import build_common_time_context, dual_timezone_display, is_client

logger = logging.getLogger("hotel")


def home_view(request):
    common_context = build_common_time_context(request)
    user_tz = ZoneInfo(common_context["user_timezone_name"])
    latest_article = None
    try:
        latest_article = Article.objects.latest("created_at")
    except Article.DoesNotExist:
        latest_article = None

    categories = RoomCategory.objects.all()
    rooms = Room.objects.select_related("category").all()
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    category_id = request.GET.get("category")

    if category_id:
        rooms = rooms.filter(category_id=category_id)
    if min_price:
        try:
            rooms = rooms.filter(category__base_price__gte=Decimal(min_price))
        except InvalidOperation:
            messages.error(request, "Некорректный формат минимальной цены.")
    if max_price:
        try:
            rooms = rooms.filter(category__base_price__lte=Decimal(max_price))
        except InvalidOperation:
            messages.error(request, "Некорректный формат максимальной цены.")

    context = {
        "latest_article": latest_article,
        "categories": categories,
        "rooms": rooms,
        "can_book": is_client(request.user) or request.user.is_superuser,
        "weather_data": get_weather_data(city="Minsk"),
        "currency_data": get_external_data(base="BYN"),
        "weather_city": "Минск",
        "currency_base": "BYN",
    }
    if latest_article:
        context["latest_article_times"] = dual_timezone_display(
            latest_article.created_at, user_tz
        )
    context.update(common_context)
    return render(request, "hotel/home.html", context)


def about_view(request):
    common_context = build_common_time_context(request)
    company_info = CompanyInfo.objects.first()
    return render(
        request,
        "hotel/about.html",
        {"company_info": company_info, **common_context},
    )


@login_required(login_url="login")
@user_passes_test(lambda u: u.is_superuser)
def company_info_update_view(request):
    common_context = build_common_time_context(request)
    instance = CompanyInfo.objects.first()
    if request.method == "POST":
        form = CompanyInfoForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Информация о компании обновлена.")
            return redirect("about")
    else:
        form = CompanyInfoForm(instance=instance)
    return render(request, "hotel/about_form.html", {"form": form, **common_context})


@login_required(login_url="login")
@user_passes_test(lambda u: u.is_superuser)
def company_info_delete_view(request):
    common_context = build_common_time_context(request)
    instance = CompanyInfo.objects.first()
    if request.method == "POST":
        if instance:
            instance.delete()
            messages.success(request, "Информация о компании удалена.")
        return redirect("about")
    return render(request, "hotel/confirm_delete.html", {"object": instance, **common_context})


def privacy_view(request):
    common_context = build_common_time_context(request)
    return render(request, "hotel/privacy.html", common_context)
