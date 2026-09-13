import pytest
from django.test import Client


@pytest.mark.django_db
def test_analytics_forbidden_for_anonymous():
    client = Client()
    response = client.get("/analytics/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_analytics_forbidden_for_non_superuser(django_user_model):
    user = django_user_model.objects.create_user(username="c1", password="pass12345")
    client = Client()
    client.force_login(user)
    response = client.get("/analytics/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_analytics_creates_demand_chart_for_superuser(django_user_model):
    admin = django_user_model.objects.create_superuser(
        username="admin", password="pass12345", email="a@a.com"
    )
    client = Client()
    client.force_login(admin)
    response = client.get("/analytics/")
    assert response.status_code == 200
    assert b"<img" in response.content


@pytest.mark.django_db
def test_room_create_forbidden_for_non_superuser(django_user_model):
    user = django_user_model.objects.create_user(username="u1", password="pass12345")
    client = Client()
    client.force_login(user)
    response = client.get("/rooms/create/")
    assert response.status_code == 403
