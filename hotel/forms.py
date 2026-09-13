import re
import logging
from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Article, Booking, Client, CompanyInfo, Employee, ExtraService, Glossary, Payment, PromoCode, Review, Room, RoomCategory, Vacancy


BY_PHONE_PATTERN = r"^\+375 \((29|33|44|25)\) \d{3}-\d{2}-\d{2}$"

COMMON_TIMEZONES = [
    ("Europe/Minsk", "Минск (Europe/Minsk)"),
    ("Europe/Moscow", "Москва (Europe/Moscow)"),
    ("Europe/Kaliningrad", "Калининград (Europe/Kaliningrad)"),
    ("Europe/London", "Лондон (Europe/London)"),
    ("Europe/Paris", "Париж (Europe/Paris)"),
    ("Europe/Berlin", "Берлин (Europe/Berlin)"),
    ("America/New_York", "Нью-Йорк (America/New_York)"),
    ("America/Chicago", "Чикаго (America/Chicago)"),
    ("America/Denver", "Денвер (America/Denver)"),
    ("America/Los_Angeles", "Лос-Анджелес (America/Los_Angeles)"),
    ("Asia/Tokyo", "Токио (Asia/Tokyo)"),
    ("Asia/Shanghai", "Шанхай (Asia/Shanghai)"),
    ("Asia/Vladivostok", "Владивосток (Asia/Vladivostok)"),
    ("Asia/Yekaterinburg", "Екатеринбург (Asia/Yekaterinburg)"),
    ("Asia/Almaty", "Алматы (Asia/Almaty)"),
    ("Australia/Sydney", "Сидней (Australia/Sydney)"),
]

logger = logging.getLogger("hotel")


class UserLoginForm(AuthenticationForm):
    pass


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "required": "required",
                "pattern": BY_PHONE_PATTERN,
                "placeholder": "+375 (XX) XXX-XX-XX",
            }
        ),
    )
    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "required": "required"}),
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.match(BY_PHONE_PATTERN, phone):
            logger.warning("UserRegistrationForm invalid phone: %r", phone)
            raise forms.ValidationError(
                "Телефон должен быть в формате +375 (XX) XXX-XX-XX."
            )
        return phone

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            logger.warning("UserRegistrationForm underage: %s", birth_date)
            raise forms.ValidationError("Регистрация разрешена только для лиц старше 18 лет.")
        return birth_date



class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            "last_name",
            "first_name",
            "patronymic",
            "phone",
            "birth_date",
            "comment",
            "timezone",
        )
        widgets = {
            "last_name": forms.TextInput(attrs={"required": "required"}),
            "first_name": forms.TextInput(attrs={"required": "required"}),
            "patronymic": forms.TextInput(),
            "phone": forms.TextInput(
                attrs={
                    "required": "required",
                    "pattern": BY_PHONE_PATTERN,
                    "placeholder": "+375 (XX) XXX-XX-XX",
                }
            ),
            "birth_date": forms.DateInput(attrs={"type": "date", "required": "required"}),
            "work_description": forms.Textarea(attrs={"required": "required", "rows": 4}),
            "timezone": forms.Select(choices=COMMON_TIMEZONES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].required = True
        self.fields["first_name"].required = True
        if self.instance and self.instance.pk:
            self.fields["user"] = forms.CharField(
                initial=self.instance.user.username,
                disabled=True,
                required=False,
                label="Пользователь",
            )
            self.fields["email"] = forms.EmailField(
                initial=self.instance.user.email,
                required=False,
                label="Email",
            )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.match(BY_PHONE_PATTERN, phone):
            logger.warning("ClientProfileForm invalid phone: %r", phone)
            raise forms.ValidationError(
                "Телефон должен быть в формате +375 (29) XXX-XX-XX."
            )
        return phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            logger.warning("ClientProfileForm underage validation error: %s", birth_date)
            raise forms.ValidationError(
                "Регистрация разрешена только для лиц старше 18 лет."
            )
        return birth_date

    def clean(self):
        cleaned_data = super().clean()
        parts = [
            cleaned_data.get("last_name", ""),
            cleaned_data.get("first_name", ""),
            cleaned_data.get("patronymic", ""),
        ]
        cleaned_data["full_name"] = " ".join(p for p in parts if p).strip()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        parts = [instance.last_name, instance.first_name, instance.patronymic]
        instance.full_name = " ".join(p for p in parts if p).strip()
        if commit:
            instance.save()
            if self.cleaned_data.get("email"):
                instance.user.email = self.cleaned_data["email"]
                instance.user.save(update_fields=["email"])
        return instance



class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = (
            "last_name",
            "first_name",
            "patronymic",
            "position",
            "phone",
            "birth_date",
            "photo",
            "work_description",
            "timezone",
        )
        widgets = {
            "position": forms.TextInput(attrs={"required": "required"}),
            "phone": forms.TextInput(
                attrs={
                    "required": "required",
                    "pattern": BY_PHONE_PATTERN,
                    "placeholder": "+375 (29) 123-45-67",
                }
            ),
            "birth_date": forms.DateInput(attrs={"type": "date", "required": "required"}),
            "work_description": forms.Textarea(attrs={"required": "required", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["email"] = forms.EmailField(
                initial=self.instance.user.email,
                required=False,
                label="Email",
            )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.match(BY_PHONE_PATTERN, phone):
            logger.warning("EmployeeProfileForm invalid phone: %r", phone)
            raise forms.ValidationError(
                "Телефон должен быть в формате +375 (29) XXX-XX-XX."
            )
        return phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            logger.warning("EmployeeProfileForm underage validation error: %s", birth_date)
            raise forms.ValidationError(
                "Регистрация разрешена только для лиц старше 18 лет."
            )
        return birth_date

    def clean(self):
        cleaned_data = super().clean()
        parts = [
            cleaned_data.get("last_name", ""),
            cleaned_data.get("first_name", ""),
            cleaned_data.get("patronymic", ""),
        ]
        cleaned_data["full_name"] = " ".join(p for p in parts if p).strip()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        parts = [instance.last_name, instance.first_name, instance.patronymic]
        instance.full_name = " ".join(p for p in parts if p).strip()
        if commit:
            instance.save()
            if self.cleaned_data.get("email"):
                instance.user.email = self.cleaned_data["email"]
                instance.user.save(update_fields=["email"])
        return instance


class EmployeeAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(employee_profile__isnull=True),
        required=True,
    )

    class Meta:
        model = Employee
        fields = (
            "user",
            "last_name",
            "first_name",
            "patronymic",
            "position",
            "phone",
            "birth_date",
            "photo",
            "work_description",
            "timezone",
        )
        widgets = {
            "position": forms.TextInput(attrs={"required": "required"}),
            "phone": forms.TextInput(
                attrs={
                    "required": "required",
                    "pattern": BY_PHONE_PATTERN,
                    "placeholder": "+375 (29) 123-45-67",
                }
            ),
            "birth_date": forms.DateInput(attrs={"type": "date", "required": "required"}),
            "work_description": forms.Textarea(attrs={"required": "required", "rows": 4}),
            "timezone": forms.Select(choices=COMMON_TIMEZONES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["user"] = forms.CharField(
                initial=self.instance.user.username,
                disabled=True,
                required=False,
                label="Пользователь",
            )
            self.fields["email"] = forms.EmailField(
                initial=self.instance.user.email,
                required=False,
                label="Email",
            )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.match(BY_PHONE_PATTERN, phone):
            logger.warning("EmployeeProfileForm invalid phone: %r", phone)
            raise forms.ValidationError(
                "Телефон должен быть в формате +375 (29) XXX-XX-XX."
            )
        return phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            logger.warning("EmployeeProfileForm underage validation error: %s", birth_date)
            raise forms.ValidationError(
                "Регистрация разрешена только для лиц старше 18 лет."
            )
        return birth_date

    def clean(self):
        cleaned_data = super().clean()
        parts = [
            cleaned_data.get("last_name", ""),
            cleaned_data.get("first_name", ""),
            cleaned_data.get("patronymic", ""),
        ]
        cleaned_data["full_name"] = " ".join(p for p in parts if p).strip()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        parts = [instance.last_name, instance.first_name, instance.patronymic]
        instance.full_name = " ".join(p for p in parts if p).strip()
        if commit:
            instance.save()
            if self.cleaned_data.get("email"):
                instance.user.email = self.cleaned_data["email"]
                instance.user.save(update_fields=["email"])
        return instance


class BookingForm(forms.Form):
    room = forms.ModelChoiceField(
        queryset=Room.objects.select_related("category").all(),
        required=True,
    )
    date_from = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "required": "required"}),
    )
    date_to = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "required": "required"}),
    )
    extra_services = forms.ModelMultipleChoiceField(
        queryset=ExtraService.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if not room or not date_from or not date_to:
            return cleaned_data

        if date_to <= date_from:
            logger.warning(
                "BookingForm invalid date range: from=%s to=%s", date_from, date_to
            )
            raise forms.ValidationError("Дата выезда должна быть строго позже даты заезда!")

        has_overlap = Booking.objects.filter(
            room=room,
            status=Booking.BookingStatus.ACTIVE,
        ).filter(
            Q(check_in_date__lt=date_to) & Q(check_out_date__gt=date_from)
        ).exists()

        if has_overlap:
            logger.warning(
                "BookingForm overbooking attempt room=%s from=%s to=%s",
                room.pk,
                date_from,
                date_to,
            )
            raise forms.ValidationError(
                "Данный номер уже забронирован на указанные даты!"
            )

        return cleaned_data


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ("booking", "amount", "paid_at", "status")
        widgets = {
            "paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class CartPaymentForm(forms.Form):
    cardholder = forms.CharField(required=True, min_length=3, max_length=100)
    card = forms.RegexField(required=True, regex=r"^\d{4} \d{4} \d{4} \d{4}$")
    exp = forms.CharField(required=True, widget=forms.TextInput(attrs={"type": "month"}))
    cvc = forms.RegexField(required=True, regex=r"^\d{3,4}$")
    email = forms.EmailField(required=True)
    method = forms.ChoiceField(
        required=True,
        choices=[("card", "Банковская карта"), ("erip", "ЕРИП"), ("cash", "Наличные на ресепшене")],
    )
    agree = forms.BooleanField(required=True)


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("room_number", "status", "category", "photo")
        widgets = {
            "room_number": forms.TextInput(attrs={"required": "required"}),
            "status": forms.Select(attrs={"required": "required"}),
            "category": forms.Select(attrs={"required": "required"}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class RoomCategoryForm(forms.ModelForm):
    class Meta:
        model = RoomCategory
        fields = ("name", "capacity", "description", "base_price")
        widgets = {
            "name": forms.TextInput(attrs={"required": "required"}),
            "capacity": forms.NumberInput(attrs={"required": "required", "min": 1}),
            "description": forms.Textarea(attrs={"required": "required", "rows": 3}),
            "base_price": forms.NumberInput(
                attrs={"required": "required", "min": "0", "step": "0.01"}
            ),
        }


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ("title", "short_content", "full_text", "image")
        widgets = {
            "title": forms.TextInput(attrs={"required": "required"}),
            "short_content": forms.TextInput(attrs={"required": "required"}),
            "full_text": forms.Textarea(attrs={"required": "required", "rows": 6}),
        }


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = ("title", "description", "requirements", "salary_level")
        widgets = {
            "title": forms.TextInput(attrs={"required": "required"}),
            "description": forms.Textarea(attrs={"required": "required", "rows": 4}),
            "requirements": forms.Textarea(attrs={"required": "required", "rows": 4}),
            "salary_level": forms.TextInput(attrs={"required": "required"}),
        }


class GlossaryForm(forms.ModelForm):
    class Meta:
        model = Glossary
        fields = ("question", "answer")
        widgets = {
            "question": forms.TextInput(attrs={"required": "required"}),
            "answer": forms.Textarea(attrs={"required": "required", "rows": 4}),
        }


class ExtraServiceForm(forms.ModelForm):
    class Meta:
        model = ExtraService
        fields = ("name", "price")
        widgets = {
            "name": forms.TextInput(attrs={"required": "required"}),
            "price": forms.NumberInput(attrs={"required": "required", "min": "0", "step": "0.01"}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("author_name", "rating", "review_text")
        widgets = {
            "author_name": forms.TextInput(attrs={"required": "required"}),
            "rating": forms.NumberInput(attrs={"required": "required", "min": 1, "max": 5}),
            "review_text": forms.Textarea(attrs={"required": "required", "rows": 4}),
        }


class CompanyInfoForm(forms.ModelForm):
    class Meta:
        model = CompanyInfo
        fields = ("company_text", "history_by_years", "company_details")
        widgets = {
            "company_text": forms.Textarea(attrs={"required": "required", "rows": 6}),
            "history_by_years": forms.Textarea(attrs={"required": "required", "rows": 6}),
            "company_details": forms.Textarea(attrs={"required": "required", "rows": 6}),
        }


class PromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = ("code", "discount_percent", "status")
        widgets = {
            "code": forms.TextInput(attrs={"required": "required"}),
            "discount_percent": forms.NumberInput(attrs={"required": "required", "min": "0", "max": "100", "step": "0.01"}),
        }


class BookingManageForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = (
            "room",
            "client",
            "check_in_date",
            "check_out_date",
            "total_cost",
            "status",
        )
        widgets = {
            "check_in_date": forms.DateInput(attrs={"type": "date", "required": "required"}),
            "check_out_date": forms.DateInput(attrs={"type": "date", "required": "required"}),
            "total_cost": forms.NumberInput(
                attrs={"required": "required", "min": "0", "step": "0.01"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        room = cleaned_data.get("room")
        date_from = cleaned_data.get("check_in_date")
        date_to = cleaned_data.get("check_out_date")

        if not room or not date_from or not date_to:
            return cleaned_data

        if date_to <= date_from:
            logger.warning(
                "BookingManageForm invalid date range: from=%s to=%s",
                date_from,
                date_to,
            )
            raise forms.ValidationError("Дата выезда должна быть строго позже даты заезда!")

        overlaps = Booking.objects.filter(
            room=room,
            status=Booking.BookingStatus.ACTIVE,
            check_in_date__lt=date_to,
            check_out_date__gt=date_from,
        )
        if self.instance.pk:
            overlaps = overlaps.exclude(pk=self.instance.pk)

        if overlaps.exists():
            logger.warning(
                "BookingManageForm overbooking attempt booking_id=%s room=%s from=%s to=%s",
                self.instance.pk,
                room.pk,
                date_from,
                date_to,
            )
            raise forms.ValidationError(
                "Данный номер уже забронирован на указанные даты!"
            )

        return cleaned_data

        
