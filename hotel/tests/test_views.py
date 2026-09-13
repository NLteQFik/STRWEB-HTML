from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import Client as DjangoTestClient
from django.test import RequestFactory

from hotel.models import (
    Article,
    Booking,
    Client,
    Employee,
    ExtraService,
    Glossary,
    Payment,
    PromoCode,
    Review,
    Room,
    RoomCategory,
    Vacancy,
)
from hotel.utils import get_user_timezone
from hotel.views import (
    apply_request_timezone,
    build_common_time_context,
    dual_timezone_display,
    get_age,
    is_client,
    is_employee,
)


@pytest.mark.django_db
def test_is_employee_true(django_user_model):
    user = django_user_model.objects.create_user(username="emp", password="pass")
    Employee.objects.create(
        user=user, full_name="Emp", position="Mgr", birth_date=date(1990, 1, 1),
        phone="+375 (29) 111-22-33", work_description="Mgmt", timezone="Europe/Minsk",
    )
    assert is_employee(user)


def test_is_employee_false_anonymous():
    assert not is_employee(AnonymousUser())


@pytest.mark.django_db
def test_is_client_true(django_user_model):
    user = django_user_model.objects.create_user(username="cl", password="pass")
    assert is_client(user)


def test_is_client_false_anonymous():
    assert not is_client(AnonymousUser())


def test_get_age():
    assert get_age(date(2000, 6, 1), date(2025, 6, 1)) == 25
    assert get_age(date(2000, 6, 1), date(2025, 5, 31)) == 24


def test_dual_timezone_display_naive():
    from datetime import datetime
    dt = datetime(2025, 6, 1, 12, 0)
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Europe/Minsk")
    result = dual_timezone_display(dt, tz)
    assert "utc" in result
    assert "user" in result


def test_dual_timezone_display_aware():
    from datetime import datetime, timezone as dt_tz
    from zoneinfo import ZoneInfo
    dt = datetime(2025, 6, 1, 12, 0, tzinfo=dt_tz.utc)
    tz = ZoneInfo("Europe/Minsk")
    result = dual_timezone_display(dt, tz)
    seed = dt.day * dt.month + dt.hour
    rand_min = (seed * 17 + 7) % 60
    assert result["utc"] == f"01/06/2025 12:{rand_min:02d}"
    assert result["user"] == f"01/06/2025 15:{rand_min:02d}"


def test_apply_request_timezone(rf):
    request = rf.get("/")
    request.user = AnonymousUser()
    request.session = {}
    tz = apply_request_timezone(request)
    assert isinstance(tz, type(tz))


def test_build_common_time_context(rf):
    request = rf.get("/")
    request.user = AnonymousUser()
    request.session = {}
    ctx = build_common_time_context(request)
    assert "user_timezone_name" in ctx
    assert "today_label" in ctx
    assert "month_calendar" in ctx
    assert ctx["is_employee"] is False



@pytest.mark.django_db
def test_register_view_get():
    client = DjangoTestClient()
    response = client.get("/register/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_view_post():
    client = DjangoTestClient()
    response = client.post("/register/", {
        "username": "newuser", "password1": "Secret123!", "password2": "Secret123!",
        "email": "a@b.com", "first_name": "A", "last_name": "B",
        "phone": "+375 (29) 123-45-67", "birth_date": "2000-01-15",
    })
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_view_get():
    client = DjangoTestClient()
    response = client.get("/login/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_view_post(django_user_model):
    django_user_model.objects.create_user(username="testuser", password="pass12345")
    client = DjangoTestClient()
    response = client.post("/login/", {"username": "testuser", "password": "pass12345"})
    assert response.status_code == 302


@pytest.mark.django_db
def test_logout_view(django_user_model):
    django_user_model.objects.create_user(username="u", password="pass")
    client = DjangoTestClient()
    client.login(username="u", password="pass")
    response = client.get("/logout/")
    assert response.status_code == 302



@pytest.mark.django_db
def test_home_view():
    client = DjangoTestClient()
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_home_view_with_filter():
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="X")
    Room.objects.create(room_number="1", status=Room.RoomStatus.FREE, category=cat)
    client = DjangoTestClient()
    response = client.get(f"/?min_price=50&max_price=200&category={cat.pk}")
    assert response.status_code == 200


@pytest.mark.django_db
def test_about_view():
    client = DjangoTestClient()
    response = client.get("/about/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_privacy_view():
    client = DjangoTestClient()
    response = client.get("/privacy/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_article_list_view():
    Article.objects.create(title="A", short_content="Short", full_text="B")
    client = DjangoTestClient()
    response = client.get("/articles/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_article_list_view_with_search():
    Article.objects.create(title="Found", short_content="Short", full_text="Content")
    client = DjangoTestClient()
    response = client.get("/articles/?q=Found")
    assert response.status_code == 200


@pytest.mark.django_db
def test_article_detail_view():
    article = Article.objects.create(title="A", short_content="Short", full_text="B")
    client = DjangoTestClient()
    response = client.get(f"/articles/{article.pk}/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_review_list_view_get():
    Review.objects.create(author_name="A", rating=5, review_text="Good")
    client = DjangoTestClient()
    response = client.get("/reviews/?sort=rating_asc")
    assert response.status_code == 200


@pytest.mark.django_db
def test_review_list_view_post_by_client(django_user_model):
    django_user_model.objects.create_user(username="revuser", password="pass")
    client = DjangoTestClient()
    client.login(username="revuser", password="pass")
    response = client.post("/reviews/", {"author_name": "A", "rating": 5, "review_text": "Nice"})
    assert response.status_code == 302



@pytest.mark.django_db
def test_extra_service_list_view():
    ExtraService.objects.create(name="WiFi", price=10)
    client = DjangoTestClient()
    response = client.get("/extra-services/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_employee_list_view():
    client = DjangoTestClient()
    response = client.get("/employees/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_vacancy_list_view():
    client = DjangoTestClient()
    response = client.get("/vacancies/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_glossary_list_view():
    client = DjangoTestClient()
    response = client.get("/glossary/")
    assert response.status_code == 200



@pytest.mark.django_db
def test_promo_code_list_view():
    PromoCode.objects.create(code="SAVE10", discount_percent=10)
    client = DjangoTestClient()
    response = client.get("/promocodes/?sort=discount_percent&q=SAVE")
    assert response.status_code == 200



@pytest.mark.django_db
def test_client_cabinet_view_not_client(rf, django_user_model):
    user = django_user_model.objects.create_user(username="noc", password="pass")
    user.groups.filter(name="Client").delete()
    user.client_profile.delete()
    user = django_user_model.objects.get(pk=user.pk)
    request = rf.get("/cabinet/")
    request.user = user
    request.session = {}
    from hotel.views import client_cabinet_view
    response = client_cabinet_view(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_client_cabinet_view_get(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clcab", password="pass")
    request = rf.get("/cabinet/")
    request.user = user
    request.session = {}
    from hotel.views import client_cabinet_view
    response = client_cabinet_view(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_client_cabinet_view_post(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clcab2", password="pass")
    client = Client.objects.get(user=user)
    request = rf.post("/cabinet/", {
        "user": user.pk,
        "last_name": "New", "first_name": "Name", "patronymic": "",
        "phone": "+375 (29) 123-45-67",
        "birth_date": "1990-01-01", "children_count": 2, "timezone": "Europe/Minsk",
    })
    request.user = user
    request.session = {}
    from hotel.views import client_cabinet_view
    response = client_cabinet_view(request)
    assert response.status_code == 302



@pytest.mark.django_db
def test_booking_create_view_not_client(rf, django_user_model):
    user = django_user_model.objects.create_user(username="noc", password="pass")
    user.groups.filter(name="Client").delete()
    user.client_profile.delete()
    user = django_user_model.objects.get(pk=user.pk)
    request = rf.get("/booking/create/")
    request.user = user
    request.session = {}
    from hotel.views import booking_create_view
    response = booking_create_view(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_booking_create_view_get(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clb", password="pass")
    request = rf.get("/booking/create/")
    request.user = user
    request.session = {}
    from hotel.views import booking_create_view
    response = booking_create_view(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_booking_create_view_post(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clb2", password="pass")
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=150, description="X")
    room = Room.objects.create(room_number="B1", status=Room.RoomStatus.FREE, category=cat)
    request = rf.post("/booking/create/", {
        "room": room.pk, "date_from": "2026-07-01", "date_to": "2026-07-05",
    })
    request.user = user
    request.session = {}
    from hotel.views import booking_create_view
    response = booking_create_view(request)
    assert response.status_code == 302


@pytest.mark.django_db
def test_booking_my_list_view(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clbl", password="pass")
    Client.objects.get_or_create(user=user)
    request = rf.get("/bookings/my/")
    request.user = user
    request.session = {}
    from hotel.views import booking_user_view
    response = booking_user_view(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_booking_cancel_view(rf, django_user_model):
    user = django_user_model.objects.create_user(username="clbc", password="pass")
    client = Client.objects.get(user=user)
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="X")
    room = Room.objects.create(room_number="BC1", status=Room.RoomStatus.FREE, category=cat)
    booking = Booking.objects.create(
        room=room, client=client, check_in_date="2026-08-01", check_out_date="2026-08-05",
        total_cost=500, status=Booking.BookingStatus.ACTIVE,
    )
    request = rf.post(f"/bookings/{booking.pk}/cancel/")
    request.user = user
    request.session = {}
    from hotel.views import booking_cancel_view
    response = booking_cancel_view(request, pk=booking.pk)
    assert response.status_code == 302



@pytest.mark.django_db
def test_room_list_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su", password="pass", email="a@b.com")
    request = rf.get("/rooms/")
    request.user = user
    request.session = {}
    from hotel.views import RoomListView
    response = RoomListView.as_view()(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_room_detail_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su2", password="pass", email="a@b.com")
    cat = RoomCategory.objects.create(name="Lux", capacity=2, base_price=300, description="Lux")
    room = Room.objects.create(room_number="R1", status=Room.RoomStatus.FREE, category=cat)
    request = rf.get(f"/rooms/{room.pk}/")
    request.user = user
    request.session = {}
    from hotel.views import RoomDetailView
    response = RoomDetailView.as_view()(request, pk=room.pk)
    assert response.status_code == 200


@pytest.mark.django_db
def test_room_create_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su3", password="pass", email="a@b.com")
    cat = RoomCategory.objects.create(name="Eco", capacity=1, base_price=80, description="Eco")
    request = rf.post("/rooms/create/", {
        "room_number": "NEW1", "status": Room.RoomStatus.FREE, "category": cat.pk,
    })
    request.user = user
    request.session = {}
    from hotel.views import RoomCreateView
    response = RoomCreateView.as_view()(request)
    assert response.status_code == 302


@pytest.mark.django_db
def test_room_update_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su4", password="pass", email="a@b.com")
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Std")
    room = Room.objects.create(room_number="UP1", status=Room.RoomStatus.FREE, category=cat)
    request = rf.post(f"/rooms/{room.pk}/edit/", {
        "room_number": "UP1", "status": Room.RoomStatus.FREE, "category": cat.pk,
    })
    request.user = user
    request.session = {}
    from hotel.views import RoomUpdateView
    response = RoomUpdateView.as_view()(request, pk=room.pk)
    assert response.status_code == 302


@pytest.mark.django_db
def test_room_delete_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su5", password="pass", email="a@b.com")
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Std")
    room = Room.objects.create(room_number="DEL1", status=Room.RoomStatus.FREE, category=cat)
    request = rf.post(f"/rooms/{room.pk}/delete/")
    request.user = user
    request.session = {}
    from hotel.views import RoomDeleteView
    response = RoomDeleteView.as_view()(request, pk=room.pk)
    assert response.status_code == 302


@pytest.mark.django_db
def test_booking_list_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su6", password="pass", email="a@b.com")
    request = rf.get("/admin/bookings/")
    request.user = user
    request.session = {}
    from hotel.views import BookingListView
    response = BookingListView.as_view()(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_booking_update_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su7", password="pass", email="a@b.com")
    cl_user = django_user_model.objects.create_user(username="clx", password="pass")
    client = Client.objects.get(user=cl_user)
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Std")
    room = Room.objects.create(room_number="BU1", status=Room.RoomStatus.FREE, category=cat)
    booking = Booking.objects.create(
        room=room, client=client, check_in_date="2026-09-01", check_out_date="2026-09-05",
        total_cost=400, status=Booking.BookingStatus.ACTIVE,
    )
    request = rf.post(f"/admin/bookings/{booking.pk}/edit/", {
        "room": room.pk, "client": client.pk,
        "check_in_date": "2026-09-01", "check_out_date": "2026-09-06",
        "status": Booking.BookingStatus.ACTIVE, "total_cost": 500,
    })
    request.user = user
    request.session = {}
    from hotel.views import BookingUpdateView
    response = BookingUpdateView.as_view()(request, pk=booking.pk)
    assert response.status_code == 302


@pytest.mark.django_db
def test_booking_delete_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su8", password="pass", email="a@b.com")
    cl_user = django_user_model.objects.create_user(username="cly", password="pass")
    client = Client.objects.get(user=cl_user)
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Std")
    room = Room.objects.create(room_number="BD1", status=Room.RoomStatus.FREE, category=cat)
    booking = Booking.objects.create(
        room=room, client=client, check_in_date="2026-10-01", check_out_date="2026-10-05",
        total_cost=400, status=Booking.BookingStatus.ACTIVE,
    )
    request = rf.post(f"/admin/bookings/{booking.pk}/delete/")
    request.user = user
    request.session = {}
    from hotel.views import BookingDeleteView
    response = BookingDeleteView.as_view()(request, pk=booking.pk)
    assert response.status_code == 302



@pytest.mark.django_db
def test_room_category_list_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su9", password="pass", email="a@b.com")
    request = rf.get("/admin/categories/")
    request.user = user
    request.session = {}
    from hotel.views import RoomCategoryListView
    response = RoomCategoryListView.as_view()(request)
    assert response.status_code == 200



@pytest.mark.django_db
def test_client_list_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su10", password="pass", email="a@b.com")
    request = rf.get("/admin/clients/")
    request.user = user
    request.session = {}
    from hotel.views import ClientListView
    response = ClientListView.as_view()(request)
    assert response.status_code == 200



@pytest.mark.django_db
def test_payment_list_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su11", password="pass", email="a@b.com")
    request = rf.get("/admin/payments/")
    request.user = user
    request.session = {}
    from hotel.views import PaymentListView
    response = PaymentListView.as_view()(request)
    assert response.status_code == 200



@pytest.mark.django_db
def test_weather_api_proxy(rf, django_user_model):
    user = django_user_model.objects.create_user(username="wuser", password="pass")
    request = rf.get("/weather/")
    request.user = user
    request.session = {}
    from hotel.views import weather_api_proxy
    with patch("hotel.views.api.get_weather_data") as mock_get:
        mock_get.return_value = {"has_error": False, "temperature_c": "25"}
        response = weather_api_proxy(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_currency_api_proxy(rf, django_user_model):
    user = django_user_model.objects.create_user(username="cuser", password="pass")
    request = rf.get("/currency/")
    request.user = user
    request.session = {}
    from hotel.views import CurrencyApiProxyView
    with patch("hotel.views.api.get_external_data") as mock_get:
        mock_get.return_value = {"has_error": False, "USD": 0.31}
        response = CurrencyApiProxyView.as_view()(request)
    assert response.status_code == 200



@pytest.mark.django_db
def test_hotel_analytics_view_superuser(rf, django_user_model):
    user = django_user_model.objects.create_superuser(username="su12", password="pass", email="a@b.com")
    request = rf.get("/analytics/")
    request.user = user
    request.session = {}
    from hotel.views import hotel_analytics_view
    response = hotel_analytics_view(request)
    assert response.status_code == 200
