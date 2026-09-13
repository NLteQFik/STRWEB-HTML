from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client

from hotel.models import Room, RoomCategory


@pytest.mark.django_db
def test_room_crud_superuser(django_user_model):
    admin = django_user_model.objects.create_superuser(
        username="admin", password="pass12345", email="a@a.com"
    )
    category = RoomCategory.objects.create(
        name="Тест",
        capacity=2,
        description="Категория для теста",
        base_price=Decimal("100.00"),
    )

    client = Client()
    client.force_login(admin)

    resp_create = client.post(
        "/rooms/create/",
        data={"room_number": "999", "status": "free", "category": category.pk},
    )
    assert resp_create.status_code in {302, 200}
    assert Room.objects.filter(room_number="999").exists()

    room = Room.objects.get(room_number="999")
    resp_update = client.post(
        f"/rooms/{room.pk}/update/",
        data={"room_number": "999", "status": "occupied", "category": category.pk},
    )
    assert resp_update.status_code in {302, 200}
    room.refresh_from_db()
    assert room.status == "occupied"

    resp_delete = client.post(f"/rooms/{room.pk}/delete/")
    assert resp_delete.status_code in {302, 200}
    assert not Room.objects.filter(pk=room.pk).exists()
