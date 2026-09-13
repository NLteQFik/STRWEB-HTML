from datetime import date, timedelta

import pytest

from django import forms as django_forms

from hotel.forms import (
    BY_PHONE_PATTERN,
    BookingForm,
    BookingManageForm,
    ClientProfileForm,
    EmployeeProfileForm,
    ReviewForm,
    RoomCategoryForm,
    RoomForm,
)
from hotel.models import Booking, Client, Employee, ExtraService, Room, RoomCategory


def _safe_years_ago(years: int, extra_days: int = 0) -> date:
    today = date.today()
    try:
        base = today.replace(year=today.year - years)
    except ValueError:
        base = today.replace(month=2, day=28, year=today.year - years)
    return base + timedelta(days=extra_days)



@pytest.mark.django_db
@pytest.mark.parametrize(
    "birth_date,expected_valid",
    [
        (_safe_years_ago(18, 0), True),
        (_safe_years_ago(18, 1), False),
        (date.today() + timedelta(days=10), False),
    ],
)
def test_client_age_validation_boundary(birth_date, expected_valid, django_user_model):
    user = django_user_model.objects.create_user(username="u1", password="pass12345")
    Client.objects.filter(user=user).delete()
    form = ClientProfileForm(
        data={
            "user": user.pk,
            "last_name": "Иванов", "first_name": "Иван", "patronymic": "Иванович",
            "phone": "+375 (29) 123-45-67",
            "birth_date": birth_date,
            "timezone": "Europe/Minsk",
        }
    )
    assert form.is_valid() is expected_valid


@pytest.mark.django_db
@pytest.mark.parametrize(
    "phone,expected_valid",
    [
        ("+375 (29) 123-45-67", True),
        ("+375(29)123-45-67", False),
        ("+375 (99) 123-45-67", False),
        ("", False),
        ("abc", False),
    ],
)
def test_phone_format_validation(phone, expected_valid, django_user_model):
    user = django_user_model.objects.create_user(username="u2", password="pass12345")
    Client.objects.filter(user=user).delete()
    form = ClientProfileForm(
        data={
            "user": user.pk,
            "last_name": "Петров", "first_name": "Петр", "patronymic": "Петрович",
            "phone": phone,
            "birth_date": _safe_years_ago(30, 0),
            "timezone": "Europe/Minsk",
        }
    )
    assert form.is_valid() is expected_valid


@pytest.mark.django_db
def test_client_profile_form_edit_mode(django_user_model):
    user = django_user_model.objects.create_user(username="u3", password="pass12345")
    client = Client.objects.get(user=user)
    form = ClientProfileForm(instance=client)
    assert form.fields["user"].required is False
    assert form.fields["user"].disabled is True
    assert form.fields["user"].initial == "u3"



@pytest.mark.django_db
@pytest.mark.parametrize(
    "text,expected_valid",
    [
        ("Отличный сервис!", True),
        ("   ", False),
        ("\n\n", False),
        ("", False),
    ],
)
def test_review_form_text_strip_validation(text, expected_valid):
    form = ReviewForm(
        data={
            "author_name": "Аноним",
            "rating": 5,
            "review_text": text,
        }
    )
    assert form.is_valid() is expected_valid


def test_by_phone_pattern_is_strict_regex():
    assert BY_PHONE_PATTERN.startswith("^")
    assert BY_PHONE_PATTERN.endswith("$")


@pytest.mark.django_db
def test_review_form_save(django_user_model):
    form = ReviewForm(
        data={"author_name": "Тест", "rating": 5, "review_text": "Хороший отель"}
    )
    assert form.is_valid()
    review = form.save()
    assert review.review_text == "Хороший отель"



@pytest.mark.django_db
def test_employee_phone_validation_valid(django_user_model):
    user = django_user_model.objects.create_user(username="emp1", password="pass")
    Employee.objects.create(user=user, full_name="Сотрудник", position="Admin", phone="+375 (44) 111-22-33", timezone="Europe/Minsk", birth_date=_safe_years_ago(25, 0), work_description="Works")
    form = EmployeeProfileForm(
        data={
            "last_name": "Сотрудник", "first_name": "", "patronymic": "",
            "position": "Admin",
            "phone": "+375 (29) 111-22-33",
            "birth_date": _safe_years_ago(25, 0),
            "work_description": "Some work",
            "timezone": "Europe/Minsk",
        }
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_employee_phone_validation_invalid(django_user_model):
    user = django_user_model.objects.create_user(username="emp2", password="pass")
    Employee.objects.create(user=user, full_name="Сотрудник2", position="Admin", phone="+375 (44) 111-22-33", timezone="Europe/Minsk", birth_date=_safe_years_ago(25, 0), work_description="Works")
    form = EmployeeProfileForm(
        data={
            "last_name": "Сотрудник2", "first_name": "", "patronymic": "",
            "position": "Admin",
            "phone": "12345",
            "birth_date": _safe_years_ago(25, 0),
            "work_description": "Some work",
        }
    )
    assert not form.is_valid()


@pytest.mark.django_db
def test_employee_age_validation_underage(django_user_model):
    user = django_user_model.objects.create_user(username="emp3", password="pass")
    Employee.objects.create(user=user, full_name="Юный", position="Intern", phone="+375 (25) 111-22-33", timezone="Europe/Minsk", birth_date=_safe_years_ago(20, 0), work_description="Works")
    form = EmployeeProfileForm(
        data={
            "last_name": "Юный", "first_name": "", "patronymic": "",
            "position": "Intern",
            "phone": "+375 (25) 111-22-33",
            "birth_date": _safe_years_ago(16, 0),
        }
    )
    assert not form.is_valid()



@pytest.mark.django_db
def test_booking_form_date_range_invalid():
    form = BookingForm(
        data={
            "room": "",
            "date_from": "2025-06-10",
            "date_to": "2025-06-09",
        }
    )
    assert not form.is_valid()


@pytest.mark.django_db
def test_booking_form_overlap(django_user_model):
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Standard")
    room = Room.objects.create(room_number="101", status=Room.RoomStatus.FREE, category=cat)
    user = django_user_model.objects.create_user(username="b1", password="pass")
    client = Client.objects.get(user=user)
    Booking.objects.create(
        room=room, client=client,
        check_in_date="2025-07-01", check_out_date="2025-07-05",
        total_cost=400, status=Booking.BookingStatus.ACTIVE,
    )
    form = BookingForm(
        data={
            "room": room.pk,
            "date_from": "2025-07-02",
            "date_to": "2025-07-06",
        }
    )
    assert not form.is_valid()


@pytest.mark.django_db
def test_booking_form_no_overlap(django_user_model):
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Standard")
    room = Room.objects.create(room_number="102", status=Room.RoomStatus.FREE, category=cat)
    user = django_user_model.objects.create_user(username="b2", password="pass")
    client = Client.objects.get(user=user)
    Booking.objects.create(
        room=room, client=client,
        check_in_date="2025-06-01", check_out_date="2025-06-05",
        total_cost=400, status=Booking.BookingStatus.ACTIVE,
    )
    form = BookingForm(
        data={
            "room": room.pk,
            "date_from": "2025-06-06",
            "date_to": "2025-06-10",
        }
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_booking_form_missing_fields():
    form = BookingForm(data={})
    assert not form.is_valid()



@pytest.mark.django_db
def test_booking_manage_form_date_range_invalid():
    form = BookingManageForm(
        data={
            "room": "",
            "client": "",
            "check_in_date": "2025-06-10",
            "check_out_date": "2025-06-09",
            "status": Booking.BookingStatus.ACTIVE,
            "total_cost": 100,
        }
    )
    assert not form.is_valid()


@pytest.mark.django_db
def test_booking_manage_form_exclude_self(django_user_model):
    cat = RoomCategory.objects.create(name="Std", capacity=2, base_price=100, description="Standard")
    room = Room.objects.create(room_number="201", status=Room.RoomStatus.FREE, category=cat)
    user = django_user_model.objects.create_user(username="m1", password="pass")
    client = Client.objects.get(user=user)
    booking = Booking.objects.create(
        room=room, client=client,
        check_in_date="2025-08-01", check_out_date="2025-08-05",
        total_cost=400, status=Booking.BookingStatus.ACTIVE,
    )
    form = BookingManageForm(
        data={
            "room": room.pk,
            "client": client.pk,
            "check_in_date": "2025-08-02",
            "check_out_date": "2025-08-04",
            "status": Booking.BookingStatus.ACTIVE,
            "total_cost": 200,
        },
        instance=booking,
    )
    assert form.is_valid()



@pytest.mark.django_db
def test_room_form_valid():
    cat = RoomCategory.objects.create(name="Lux", capacity=2, base_price=200, description="Luxury")
    form = RoomForm(
        data={"room_number": "301", "status": Room.RoomStatus.FREE, "category": cat.pk}
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_room_category_form_valid():
    form = RoomCategoryForm(
        data={"name": "Economy", "capacity": 1, "description": "Budget", "base_price": 50}
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_room_category_form_invalid():
    form = RoomCategoryForm(data={})
    assert not form.is_valid()


