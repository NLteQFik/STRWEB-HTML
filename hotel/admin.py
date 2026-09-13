from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Article,
    Banner,
    Booking,
    Client,
    CompanyInfo,
    Employee,
    ExtraService,
    Glossary,
    Partner,
    Payment,
    PromoCode,
    Review,
    Room,
    RoomCategory,
    Vacancy,
)


class ClientInline(admin.StackedInline):
    model = Client
    can_delete = False
    verbose_name = "Профиль клиента"
    verbose_name_plural = "Профили клиентов"


class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name = "Профиль сотрудника"
    verbose_name_plural = "Профили сотрудников"


class CustomUserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "email", "is_staff", "profile_type")
    list_select_related = ("client_profile", "employee_profile")

    @admin.display(description="Связанный профиль")
    def profile_type(self, obj):
        if hasattr(obj, "employee_profile"):
            return f"Сотрудник: {obj.employee_profile.full_name}"
        if hasattr(obj, "client_profile"):
            return f"Клиент: {obj.client_profile.full_name}"
        return "—"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1


@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "base_price", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("capacity",)
    inlines = (RoomInline,)


@admin.register(ExtraService)
class ExtraServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "status", "category", "photo", "created_at", "updated_at")
    search_fields = ("room_number", "category__name")
    list_filter = ("status", "category")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "children_count", "timezone", "comment", "created_at")
    search_fields = ("full_name", "phone", "user__username", "comment")
    list_filter = ("children_count", "timezone")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "phone", "timezone", "created_at")
    search_fields = ("full_name", "position", "phone", "user__username")
    list_filter = ("position", "timezone")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "client",
        "check_in_date",
        "check_out_date",
        "status",
        "total_cost",
    )
    search_fields = ("room__room_number", "client__full_name")
    list_filter = ("status", "room__category")
    inlines = (PaymentInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "paid_at", "created_at")
    search_fields = ("booking__room__room_number", "booking__client__full_name")
    list_filter = ("status", "paid_at")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "short_content", "created_at", "updated_at")
    search_fields = ("title", "short_content", "full_text")


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at")
    search_fields = ("company_text", "history_by_years", "company_details")


@admin.register(Glossary)
class GlossaryAdmin(admin.ModelAdmin):
    list_display = ("question", "created_at", "updated_at")
    search_fields = ("question", "answer")


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ("title", "salary_level", "created_at", "updated_at")
    search_fields = ("title", "description", "requirements", "salary_level")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author_name", "rating", "created_at", "updated_at")
    search_fields = ("author_name", "review_text")
    list_filter = ("rating",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "status", "created_at", "updated_at")
    search_fields = ("code",)
    list_filter = ("status",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "is_active", "created_at")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title",)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url", "sort_order", "is_active", "created_at")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name",)
