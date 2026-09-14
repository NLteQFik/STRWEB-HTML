"""Проверка HTML-требований ЛР: теги с атрибутами на ключевых страницах (для защиты)."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client

from hotel.models import (
    Article,
    Banner,
    CompanyInfo,
    Employee,
    Glossary,
    Partner,
    PromoCode,
    Review,
    Room,
    RoomCategory,
    Vacancy,
)


@pytest.fixture
@pytest.mark.django_db
def seed_data(django_user_model):
    category = RoomCategory.objects.create(
        name="Стандарт", capacity=2, description="Уютный номер", base_price=Decimal("100.00")
    )
    Room.objects.create(room_number="101", status=Room.RoomStatus.FREE, category=category)
    user = django_user_model.objects.create_user(
        username="ivan", password="pass12345", email="ivan@example.com"
    )
    Employee.objects.create(
        user=user,
        full_name="Иванов Иван",
        position="Администратор",
        phone="+375 (29) 111-22-33",
        birth_date=date(1990, 1, 1),
        work_description="Встреча гостей",
        timezone="Europe/Minsk",
    )
    Article.objects.create(
        title="Открытие SPA",
        short_content="Открыт новый SPA-комплекс.",
        full_text="Подробности об открытии.",
    )
    CompanyInfo.objects.create(
        company_text="Отель Aurora.",
        history_by_years="2010 — открытие.",
        company_details="УНП 123456789.",
    )
    Banner.objects.create(
        title="Скидка",
        image_url="https://example.com/banner.jpg",
        alt_text="Баннер",
        sort_order=1,
        is_active=True,
    )
    Partner.objects.create(
        name="Booking.com",
        logo_url="https://example.com/logo.png",
        website_url="https://www.booking.com/",
        sort_order=1,
        is_active=True,
    )
    Review.objects.create(author_name="Гость", rating=5, review_text="Отлично.")
    Vacancy.objects.create(
        title="Горничная", description="Уборка", requirements="Опыт", salary_level="1000 BYN"
    )
    Glossary.objects.create(question="Заезд?", answer="С 14:00.")
    PromoCode.objects.create(code="WELCOME", discount_percent=Decimal("10.00"))
    return {"user": user}


@pytest.mark.django_db
def test_about_html_tags(seed_data):
    response = Client().get("/about/")
    assert response.status_code == 200
    for snippet in [
        "<video", "<audio", "<iframe",
        "<blockquote", "<pre><code>", "<abbr", "<del", "<ins",
        "<sub>", "<sup>", "<details>", "<summary>", "<dl>",
        'headers="hist-from', "colspan", "rowspan",
        "<tfoot>", "<colgroup>", "<wbr>",
        "<address", "download=",
    ]:
        assert snippet in response.content.decode(), snippet


@pytest.mark.django_db
def test_employee_page_tags(seed_data):
    response = Client().get("/employees/")
    assert response.status_code == 200
    content = response.content.decode()
    for snippet in [
        "<address", "<datalist", "<picture>", "<figure>",
        'type="email"', 'type="tel"', 'type="url"', 'type="date"',
        'type="number"', 'type="search"', 'type="range"', 'type="color"',
        'type="file"', "<fieldset>", "<legend>", "<textarea",
        'type="radio"', 'type="checkbox"', "required", "<select",
        "tel:", "mailto:",
    ]:
        assert snippet in content, snippet


@pytest.mark.django_db
def test_article_pages_tags(seed_data):
    client = Client()
    response = client.get("/articles/")
    assert response.status_code == 200
    content = response.content.decode()
    for snippet in ["<picture>", "<time", "datePublished", "<details>", "<figure>"]:
        assert snippet in content, snippet
    article = Article.objects.first()
    detail = client.get(f"/articles/{article.pk}/")
    assert detail.status_code == 200
    detail_content = detail.content.decode()
    for snippet in ["<time", "datePublished", "<details>", "<figure>"]:
        assert snippet in detail_content, snippet


@pytest.mark.django_db
def test_base_and_catalog_tags(seed_data):
    with patch("hotel.views.pages.get_weather_data", return_value={"has_error": True}), patch(
        "hotel.views.pages.get_external_data", return_value={"has_error": True}
    ):
        home = Client().get("/")
    assert home.status_code == 200
    home_content = home.content.decode()
    for snippet in [
        "<header>", "<nav", "<main", "<footer>", "<aside", "<section",
        "<abbr", "<optgroup", "<address", "<picture>",
        'media="(min-width: 768px)"', 'media="(max-width: 767px)"',
        "adaptive-demo", 'name="description"', 'rel="icon"',
        "itemscope", "<kbd>", "<samp>", "<var>",
    ]:
        assert snippet in home_content, snippet

    privacy = Client().get("/privacy/")
    assert privacy.status_code == 200
    privacy_content = privacy.content.decode()
    for snippet in ["<mark", "<aside", "<article"]:
        assert snippet in privacy_content, snippet

    catalog = Client().get("/catalog/")
    assert catalog.status_code == 200
    catalog_content = catalog.content.decode()
    for snippet in [
        "<table", "<caption>", "<thead>", "<tbody>", "<tfoot>",
        'headers="rc-number"', 'type="checkbox"', 'type="number"',
    ]:
        assert snippet in catalog_content, snippet
