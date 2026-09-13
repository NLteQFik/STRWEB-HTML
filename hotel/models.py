from datetime import date
from decimal import Decimal
import re

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


def validate_single_sentence(value: str) -> None:
    text = value.strip()
    if not text:
        raise ValidationError("Краткое содержание не может быть пустым.")

    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    if len(sentences) != 1:
        raise ValidationError(
            "Краткое содержание должно содержать строго одно предложение."
        )


def default_adult_birth_date() -> date:
    today = timezone.now().date()
    return date(today.year - 18, today.month, today.day)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.created_at is None:
                self.created_at = timezone.now()
            if self.updated_at is None:
                self.updated_at = timezone.now()
        else:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class RoomCategory(TimeStampedModel):
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    capacity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)], default=1
    )
    description = models.TextField(blank=False, null=False)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "Категория номера"
        verbose_name_plural = "Категории номеров"
        constraints = [
            models.CheckConstraint(
                check=~Q(name=""),
                name="room_category_name_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(description=""),
                name="room_category_description_not_empty",
            ),
            models.CheckConstraint(
                check=Q(base_price__gte=0),
                name="room_category_base_price_non_negative",
            ),
        ]

    def clean(self) -> None:
        if self.base_price is not None and self.base_price < 0:
            raise ValidationError({"base_price": "Стоимость не может быть отрицательной."})

    def __str__(self) -> str:
        return self.name


class ExtraService(TimeStampedModel):
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "Дополнительная услуга"
        verbose_name_plural = "Дополнительные услуги"
        constraints = [
            models.CheckConstraint(
                check=~Q(name=""),
                name="extra_service_name_not_empty",
            ),
            models.CheckConstraint(
                check=Q(price__gte=0),
                name="extra_service_price_non_negative",
            ),
        ]

    def clean(self) -> None:
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Цена услуги не может быть отрицательной."})

    def __str__(self) -> str:
        return self.name


class Room(TimeStampedModel):
    class RoomStatus(models.TextChoices):
        FREE = "free", "Свободен"
        OCCUPIED = "occupied", "Занят"
        CLEANING = "cleaning", "На уборке"

    room_number = models.CharField(max_length=10, unique=True, blank=False, null=False)
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.FREE,
    )
    photo = models.ImageField(upload_to="rooms/", blank=True, null=True)
    category = models.ForeignKey(
        RoomCategory,
        on_delete=models.PROTECT,
        related_name="rooms",
    )

    class Meta:
        verbose_name = "Номер"
        verbose_name_plural = "Номера"
        constraints = [
            models.CheckConstraint(
                check=~Q(room_number=""),
                name="room_number_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return f"Номер {self.room_number}"


class Client(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    full_name = models.CharField(max_length=255, blank=False, null=False, default="Новый клиент")
    last_name = models.CharField(max_length=100, blank=True, null=False, default="")
    first_name = models.CharField(max_length=100, blank=True, null=False, default="")
    patronymic = models.CharField(max_length=100, blank=True, null=False, default="")
    comment = models.TextField(blank=True, null=True)
    phone = models.CharField(
        max_length=20,
        blank=False,
        null=False,
        default="+375 (29) 000-00-00",
    )
    birth_date = models.DateField(default=default_adult_birth_date)
    children_count = models.PositiveSmallIntegerField(default=0)
    timezone = models.CharField(max_length=50, default="Europe/Minsk", blank=False, null=False)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        constraints = [
            models.CheckConstraint(check=~Q(full_name=""), name="client_full_name_not_empty"),
            models.CheckConstraint(check=~Q(phone=""), name="client_phone_not_empty"),
            models.CheckConstraint(check=~Q(timezone=""), name="client_timezone_not_empty"),
        ]

    def clean(self) -> None:
        if self.birth_date and self.birth_date > date.today():
            raise ValidationError({"birth_date": "Дата рождения не может быть в будущем."})

    def __str__(self) -> str:
        return self.full_name


class Employee(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employee_profile"
    )
    full_name = models.CharField(max_length=255, blank=False, null=False)
    last_name = models.CharField(max_length=100, blank=True, null=False, default="")
    first_name = models.CharField(max_length=100, blank=True, null=False, default="")
    patronymic = models.CharField(max_length=100, blank=True, null=False, default="")
    position = models.CharField(max_length=120, blank=False, null=False)
    phone = models.CharField(max_length=20, blank=False, null=False)
    birth_date = models.DateField(default=default_adult_birth_date)
    photo = models.ImageField(upload_to="avatars/", blank=True, null=True)
    work_description = models.TextField(blank=False, null=False)
    timezone = models.CharField(max_length=50, default="Europe/Minsk", blank=False, null=False)

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        constraints = [
            models.CheckConstraint(check=~Q(full_name=""), name="employee_full_name_not_empty"),
            models.CheckConstraint(check=~Q(position=""), name="employee_position_not_empty"),
            models.CheckConstraint(check=~Q(phone=""), name="employee_phone_not_empty"),
            models.CheckConstraint(
                check=~Q(work_description=""),
                name="employee_work_description_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(timezone=""),
                name="employee_timezone_not_empty",
            ),
        ]

    def clean(self) -> None:
        if self.birth_date and self.birth_date > date.today():
            raise ValidationError({"birth_date": "Дата рождения не может быть в будущем."})

    def __str__(self) -> str:
        return self.full_name


class Booking(TimeStampedModel):
    class BookingStatus(models.TextChoices):
        ACTIVE = "active", "Активно"
        CANCELED = "canceled", "Отменено"
        FINISHED = "finished", "Завершено"

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="bookings")
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.ACTIVE,
    )
    extra_services = models.ManyToManyField(
        ExtraService,
        related_name="bookings",
        blank=True,
    )

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        constraints = [
            models.CheckConstraint(
                check=Q(total_cost__gte=0),
                name="booking_total_cost_non_negative",
            ),
            models.CheckConstraint(
                check=Q(check_out_date__gt=models.F("check_in_date")),
                name="booking_checkout_after_checkin",
            ),
        ]

    def clean(self) -> None:
        errors = {}
        if self.total_cost is not None and self.total_cost < 0:
            errors["total_cost"] = "Итоговая стоимость не может быть отрицательной."
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                errors["check_out_date"] = "Дата выезда должна быть позже даты заезда."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"Бронирование #{self.pk or 'new'}"


class Payment(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        PAID = "paid", "Оплачено"
        PENDING = "pending", "Ожидает"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gte=0),
                name="payment_amount_non_negative",
            ),
        ]

    def clean(self) -> None:
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Сумма платежа не может быть отрицательной."})

    def __str__(self) -> str:
        return f"Платеж #{self.pk or 'new'}"


class Article(TimeStampedModel):
    title = models.CharField(max_length=200, blank=False, null=False)
    short_content = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        validators=[validate_single_sentence],
    )
    full_text = models.TextField(blank=False, null=False)
    image = models.ImageField(upload_to="charts/", blank=True, null=True)

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        constraints = [
            models.CheckConstraint(check=~Q(title=""), name="article_title_not_empty"),
            models.CheckConstraint(
                check=~Q(short_content=""),
                name="article_short_content_not_empty",
            ),
            models.CheckConstraint(check=~Q(full_text=""), name="article_full_text_not_empty"),
        ]

    def __str__(self) -> str:
        return self.title


class CompanyInfo(TimeStampedModel):
    company_text = models.TextField(blank=False, null=False)
    history_by_years = models.TextField(blank=False, null=False)
    company_details = models.TextField(blank=False, null=False)

    class Meta:
        verbose_name = "О компании"
        verbose_name_plural = "О компании"
        constraints = [
            models.CheckConstraint(
                check=~Q(company_text=""),
                name="company_info_text_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(history_by_years=""),
                name="company_info_history_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(company_details=""),
                name="company_info_details_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return "Информация о компании"


class Glossary(TimeStampedModel):
    question = models.CharField(max_length=255, blank=False, null=False)
    answer = models.TextField(blank=False, null=False)

    class Meta:
        verbose_name = "Термин / FAQ"
        verbose_name_plural = "Словарь терминов / FAQ"
        constraints = [
            models.CheckConstraint(check=~Q(question=""), name="glossary_question_not_empty"),
            models.CheckConstraint(check=~Q(answer=""), name="glossary_answer_not_empty"),
        ]

    def __str__(self) -> str:
        return self.question


class Vacancy(TimeStampedModel):
    title = models.CharField(max_length=150, blank=False, null=False)
    description = models.TextField(blank=False, null=False)
    requirements = models.TextField(blank=False, null=False)
    salary_level = models.CharField(max_length=120, blank=False, null=False)

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"
        constraints = [
            models.CheckConstraint(check=~Q(title=""), name="vacancy_title_not_empty"),
            models.CheckConstraint(
                check=~Q(description=""),
                name="vacancy_description_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(requirements=""),
                name="vacancy_requirements_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(salary_level=""),
                name="vacancy_salary_level_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Review(TimeStampedModel):
    author_name = models.CharField(max_length=120, blank=False, null=False)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    review_text = models.TextField(blank=False, null=False)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        constraints = [
            models.CheckConstraint(
                check=~Q(author_name=""),
                name="review_author_name_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(review_text=""),
                name="review_text_not_empty",
            ),
            models.CheckConstraint(
                check=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_between_1_5",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.author_name} ({self.rating}/5)"


class PromoCode(TimeStampedModel):
    class PromoStatus(models.TextChoices):
        ACTIVE = "active", "Активен"
        ARCHIVED = "archived", "В архиве"

    code = models.CharField(max_length=40, unique=True, blank=False, null=False)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=PromoStatus.choices,
        default=PromoStatus.ACTIVE,
    )

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        constraints = [
            models.CheckConstraint(check=~Q(code=""), name="promo_code_not_empty"),
            models.CheckConstraint(
                check=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name="promo_code_discount_valid_range",
            ),
        ]

    def clean(self) -> None:
        if self.discount_percent is not None and (
            self.discount_percent < 0 or self.discount_percent > 100
        ):
            raise ValidationError(
                {"discount_percent": "Скидка должна быть в диапазоне от 0 до 100."}
            )

    def __str__(self) -> str:
        return self.code
