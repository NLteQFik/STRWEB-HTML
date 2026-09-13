import calendar
import logging
from datetime import date, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.contrib.auth import login, logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect, render
from django.utils import timezone

from ..forms import UserLoginForm, UserRegistrationForm
from ..models import Client
from ..utils import get_user_timezone

logger = logging.getLogger("hotel")


def is_employee(user):
    return user.is_authenticated and (
        user.groups.filter(name="Employee").exists() or hasattr(user, "employee_profile")
    )


def is_client(user):
    return user.is_authenticated and (
        user.groups.filter(name="Client").exists() or hasattr(user, "client_profile")
    )


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class StaffOrSuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or is_employee(self.request.user)


def get_age(birth_date: date, on_date: date) -> int:
    return on_date.year - birth_date.year - (
        (on_date.month, on_date.day) < (birth_date.month, birth_date.day)
    )


def dual_timezone_display(dt_value, user_tz: ZoneInfo) -> dict[str, str]:
    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, dt_timezone.utc)
    seed = dt_value.day * dt_value.month + dt_value.hour
    rand_min = (seed * 17 + 7) % 60
    rand_sec = (seed * 31 + 13) % 60
    dt_value = dt_value.replace(minute=rand_min, second=rand_sec, microsecond=0)
    utc_dt = dt_value.astimezone(dt_timezone.utc)
    local_dt = dt_value.astimezone(user_tz)
    return {
        "utc": utc_dt.strftime("%d/%m/%Y %H:%M"),
        "user": local_dt.strftime("%d/%m/%Y %H:%M"),
    }


def apply_request_timezone(request):
    tz = get_user_timezone(request)
    timezone.activate(tz)
    return tz


def build_common_time_context(request):
    tz = apply_request_timezone(request)
    now_local = timezone.now().astimezone(tz)
    now_utc = timezone.now().astimezone(dt_timezone.utc)
    month_calendar = calendar.TextCalendar().formatmonth(now_local.year, now_local.month)
    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    return {
        "user_timezone_name": str(tz),
        "today_label": now_local.strftime("%d/%m/%Y"),
        "user_now": now_local,
        "weekday_name": weekday_names[now_local.weekday()],
        "current_date_utc": now_utc.strftime("%d/%m/%Y %H:%M"),
        "current_datetime_user": now_local.strftime("%d/%m/%Y %H:%M:%S"),
        "month_calendar": month_calendar,
        "text_calendar": month_calendar,
        "is_employee": is_employee(request.user) if request.user.is_authenticated else False,
    }


def register_view(request):
    common_context = build_common_time_context(request)
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            client = user.client_profile
            client.birth_date = form.cleaned_data["birth_date"]
            client.phone = form.cleaned_data["phone"]
            client.first_name = user.first_name or ""
            client.last_name = user.last_name or ""
            client.full_name = f"{user.last_name} {user.first_name}".strip() or user.username
            client.save(update_fields=["birth_date", "phone", "first_name", "last_name", "full_name"])
            login(request, user)
            logger.info("User registered and logged in: %s", user.username)
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "hotel/register.html", {"form": form, **common_context})


def login_view(request):
    common_context = build_common_time_context(request)
    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info("User login success: %s", user.username)
            return redirect("home")
        logger.warning("User login validation failed: %s", form.errors)
    else:
        form = UserLoginForm(request)
    return render(request, "hotel/login.html", {"form": form, **common_context})


def logout_view(request):
    apply_request_timezone(request)
    if request.user.is_authenticated:
        logger.info("User logout: %s", request.user.username)
    logout(request)
    return redirect("home")


def set_timezone_view(request):
    tz = request.GET.get("tz") or request.POST.get("tz")
    if tz:
        request.session["user_timezone"] = tz
    return redirect(request.META.get("HTTP_REFERER", "home"))
