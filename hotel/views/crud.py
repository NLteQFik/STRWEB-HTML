import logging
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import (
    ArticleForm,
    BookingForm,
    BookingManageForm,
    ClientProfileForm,
    EmployeeAdminForm,
    ExtraServiceForm,
    GlossaryForm,
    PaymentForm,
    PromoCodeForm,
    ReviewForm,
    RoomCategoryForm,
    RoomForm,
    VacancyForm,
)
from ..models import (
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
from .auth import (
    SuperuserRequiredMixin,
    StaffOrSuperuserRequiredMixin,
    apply_request_timezone,
    build_common_time_context,
    dual_timezone_display,
    get_user_timezone,
    is_client,
)

logger = logging.getLogger("hotel")


class ArticleListView(ListView):
    model = Article
    template_name = "hotel/article_list.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Article.objects.all().order_by("-created_at")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(full_text__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        common_context = build_common_time_context(self.request)
        user_tz = ZoneInfo(common_context["user_timezone_name"])
        context["article_rows"] = [
            {"article": article, "times": dual_timezone_display(article.created_at, user_tz)}
            for article in context["articles"]
        ]
        context.update(common_context)
        return context


class ArticleDetailView(DetailView):
    model = Article
    template_name = "hotel/article_detail.html"
    context_object_name = "article"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        common_context = build_common_time_context(self.request)
        user_tz = ZoneInfo(common_context["user_timezone_name"])
        context["article_created_times"] = dual_timezone_display(
            self.object.created_at, user_tz
        )
        context["article_updated_times"] = dual_timezone_display(
            self.object.updated_at, user_tz
        )
        context.update(common_context)
        return context


def review_list_view(request):
    common_context = build_common_time_context(request)
    user_tz = ZoneInfo(common_context["user_timezone_name"])
    reviews = Review.objects.all()
    sort = request.GET.get("sort", "-created_at")
    sort_map = {
        "rating_asc": "rating",
        "rating_desc": "-rating",
        "date_asc": "created_at",
        "date_desc": "-created_at",
    }
    reviews = reviews.order_by(sort_map.get(sort, "-created_at"))

    form = None
    if is_client(request.user) or request.user.is_superuser:
        if request.method == "POST":
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                if not review.author_name.strip():
                    review.author_name = request.user.get_full_name() or request.user.username
                review.save()
                logger.info("Review created by user=%s review_id=%s", request.user.username, review.pk)
                return HttpResponseRedirect(reverse_lazy("review_list"))
            logger.warning("Review form validation failed: %s", form.errors)
        else:
            form = ReviewForm(
                initial={"author_name": request.user.get_full_name() or request.user.username}
            )

    return render(
        request,
        "hotel/review_list.html",
        {
            "reviews": reviews,
            "review_rows": [
                {
                    "review": review,
                    "created_times": dual_timezone_display(review.created_at, user_tz),
                    "updated_times": dual_timezone_display(review.updated_at, user_tz),
                }
                for review in reviews
            ],
            "form": form,
            "selected_sort": sort,
            **common_context,
        },
    )


@login_required(login_url="login")
@user_passes_test(lambda u: u.is_superuser)
def review_delete_view(request, pk):
    review = get_object_or_404(Review, pk=pk)
    common_context = build_common_time_context(request)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Отзыв удалён.")
        return redirect("review_list")
    return render(request, "hotel/confirm_delete.html", {"object": review, **common_context})


class ExtraServiceListView(ListView):
    model = ExtraService
    template_name = "hotel/extra_service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        apply_request_timezone(self.request)
        return ExtraService.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


@login_required(login_url="login")
def client_cabinet_view(request):
    common_context = build_common_time_context(request)
    if not is_client(request.user):
        return HttpResponseForbidden("Доступ только для клиентов.")

    profile = request.user.client_profile
    if request.method == "POST":
        form = ClientProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("client_cabinet")
    else:
        form = ClientProfileForm(instance=profile)

    return render(
        request,
        "hotel/client_cabinet.html",
        {"form": form, "profile": profile, **common_context},
    )


class EmployeeListView(ListView):
    model = Employee
    template_name = "hotel/employee_list.html"
    context_object_name = "employees"

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Employee.objects.all()
        query = self.request.GET.get("q", "").strip()
        sort = self.request.GET.get("sort", "full_name")
        if query:
            queryset = queryset.filter(full_name__icontains=query)
        if sort in {"full_name", "-full_name", "position", "-position", "created_at"}:
            queryset = queryset.order_by(sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class EmployeeCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeAdminForm
    template_name = "hotel/employee_form.html"
    success_url = reverse_lazy("employee_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class EmployeeUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeAdminForm
    template_name = "hotel/employee_form.html"
    success_url = reverse_lazy("employee_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class EmployeeDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Employee
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("employee_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class VacancyListView(ListView):
    model = Vacancy
    template_name = "hotel/vacancy_list.html"
    context_object_name = "vacancies"

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Vacancy.objects.all()
        query = self.request.GET.get("q", "").strip()
        sort = self.request.GET.get("sort", "title")
        if query:
            queryset = queryset.filter(title__icontains=query)
        if sort in {"title", "-title", "created_at", "-created_at"}:
            queryset = queryset.order_by(sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class GlossaryListView(ListView):
    model = Glossary
    template_name = "hotel/glossary_list.html"
    context_object_name = "items"

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Glossary.objects.all()
        query = self.request.GET.get("q", "").strip()
        sort = self.request.GET.get("sort", "question")
        if query:
            queryset = queryset.filter(question__icontains=query)
        if sort in {"question", "-question", "created_at", "-created_at"}:
            queryset = queryset.order_by(sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


def promo_code_list_view(request):
    common_context = build_common_time_context(request)
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "code")
    if sort not in {"code", "-code", "discount_percent", "-discount_percent"}:
        sort = "code"

    active_codes = PromoCode.objects.filter(status=PromoCode.PromoStatus.ACTIVE)
    archived_codes = PromoCode.objects.filter(status=PromoCode.PromoStatus.ARCHIVED)
    if query:
        active_codes = active_codes.filter(code__icontains=query)
        archived_codes = archived_codes.filter(code__icontains=query)

    return render(
        request,
        "hotel/promocode_list.html",
        {
            "active_codes": active_codes.order_by(sort),
            "archived_codes": archived_codes.order_by(sort),
            "query": query,
            "selected_sort": sort,
            **common_context,
        },
    )


class RoomListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Room
    template_name = "hotel/room_list.html"
    context_object_name = "rooms"
    raise_exception = True

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Room.objects.select_related("category").all()
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        sort = self.request.GET.get("sort", "category__base_price")
        if query:
            queryset = queryset.filter(
                Q(room_number__icontains=query) | Q(category__description__icontains=query)
            )
        if status in dict(Room.RoomStatus.choices):
            queryset = queryset.filter(status=status)
        if sort in {"category__base_price", "-category__base_price"}:
            queryset = queryset.order_by(sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    model = Room
    template_name = "hotel/room_detail.html"
    context_object_name = "room"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = "hotel/room_form.html"
    success_url = reverse_lazy("room_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Room
    form_class = RoomForm
    template_name = "hotel/room_form.html"
    success_url = reverse_lazy("room_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Room
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("room_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ArticleCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "hotel/article_form.html"
    success_url = reverse_lazy("article_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ArticleUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = "hotel/article_form.html"
    success_url = reverse_lazy("article_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ArticleDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Article
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("article_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class VacancyCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Vacancy
    form_class = VacancyForm
    template_name = "hotel/vacancy_form.html"
    success_url = reverse_lazy("vacancy_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class VacancyUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Vacancy
    form_class = VacancyForm
    template_name = "hotel/vacancy_form.html"
    success_url = reverse_lazy("vacancy_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class VacancyDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Vacancy
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("vacancy_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class GlossaryCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Glossary
    form_class = GlossaryForm
    template_name = "hotel/glossary_form.html"
    success_url = reverse_lazy("glossary_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class GlossaryUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Glossary
    form_class = GlossaryForm
    template_name = "hotel/glossary_form.html"
    success_url = reverse_lazy("glossary_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class GlossaryDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Glossary
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("glossary_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ExtraServiceCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = ExtraService
    form_class = ExtraServiceForm
    template_name = "hotel/extra_service_form.html"
    success_url = reverse_lazy("extra_service_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ExtraServiceUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = ExtraService
    form_class = ExtraServiceForm
    template_name = "hotel/extra_service_form.html"
    success_url = reverse_lazy("extra_service_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ExtraServiceDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = ExtraService
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("extra_service_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class PromoCodeCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = PromoCode
    form_class = PromoCodeForm
    template_name = "hotel/promocode_form.html"
    success_url = reverse_lazy("promocode_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class PromoCodeUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = PromoCode
    form_class = PromoCodeForm
    template_name = "hotel/promocode_form.html"
    success_url = reverse_lazy("promocode_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class PromoCodeDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = PromoCode
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("promocode_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


@login_required(login_url="login")
def booking_create_view(request):
    common_context = build_common_time_context(request)
    if not is_client(request.user):
        return HttpResponseForbidden("Только клиент может создавать бронирование.")

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = Booking.objects.create(
                room=form.cleaned_data["room"],
                client=request.user.client_profile,
                check_in_date=form.cleaned_data["date_from"],
                check_out_date=form.cleaned_data["date_to"],
                total_cost=form.cleaned_data["room"].category.base_price,
                status=Booking.BookingStatus.ACTIVE,
            )
            booking.extra_services.set(form.cleaned_data["extra_services"])
            logger.info(
                "Booking created id=%s room=%s client=%s",
                booking.pk,
                booking.room.room_number,
                booking.client.full_name,
            )
            return redirect("booking_user")
        logger.warning("Booking form validation failed: %s", form.errors)
    else:
        form = BookingForm()
    return render(request, "hotel/booking_form.html", {"form": form, **common_context})


class BookingListView(LoginRequiredMixin, StaffOrSuperuserRequiredMixin, ListView):
    model = Booking
    template_name = "hotel/booking_list.html"
    context_object_name = "bookings"
    raise_exception = True

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Booking.objects.select_related("room", "client").all()
        sort = self.request.GET.get("sort", "-created_at")
        if sort in {"created_at", "-created_at", "check_in_date", "-check_in_date"}:
            queryset = queryset.order_by(sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        common_context = build_common_time_context(self.request)
        user_tz = ZoneInfo(common_context["user_timezone_name"])
        context["booking_rows"] = [
            {
                "booking": booking,
                "created_times": dual_timezone_display(booking.created_at, user_tz),
                "updated_times": dual_timezone_display(booking.updated_at, user_tz),
            }
            for booking in context["bookings"]
        ]
        context.update(common_context)
        return context


class BookingUpdateView(LoginRequiredMixin, StaffOrSuperuserRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingManageForm
    template_name = "hotel/booking_manage_form.html"
    success_url = reverse_lazy("booking_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        user_tz = get_user_timezone(self.request)
        booking = self.object
        context["created_times"] = dual_timezone_display(booking.created_at, user_tz)
        context["updated_times"] = dual_timezone_display(booking.updated_at, user_tz)
        return context


class BookingDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Booking
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("booking_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomCategoryListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = RoomCategory
    template_name = "hotel/room_category_list.html"
    context_object_name = "categories"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomCategoryCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = RoomCategory
    form_class = RoomCategoryForm
    template_name = "hotel/room_category_form.html"
    success_url = reverse_lazy("room_category_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomCategoryUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = RoomCategory
    form_class = RoomCategoryForm
    template_name = "hotel/room_category_form.html"
    success_url = reverse_lazy("room_category_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class RoomCategoryDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = RoomCategory
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("room_category_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ClientListView(LoginRequiredMixin, StaffOrSuperuserRequiredMixin, ListView):
    model = Client
    template_name = "hotel/client_list.html"
    context_object_name = "clients"
    raise_exception = True

    def get_queryset(self):
        apply_request_timezone(self.request)
        queryset = Client.objects.select_related("user").all()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(full_name__icontains=query)
        return queryset.order_by("full_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ClientCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Client
    form_class = ClientProfileForm
    template_name = "hotel/client_form.html"
    success_url = reverse_lazy("client_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ClientUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Client
    form_class = ClientProfileForm
    template_name = "hotel/client_form.html"
    success_url = reverse_lazy("client_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class ClientDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Client
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("client_list")
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_common_time_context(self.request))
        return context


class PaymentListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Payment
    template_name = "hotel/payment_list.html"
    context_object_name = "payments"
    raise_exception = True

    def get_queryset(self):
        apply_request_timezone(self.request)
        return Payment.objects.select_related("booking", "booking__room", "booking__client").all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        common_context = build_common_time_context(self.request)
        user_tz = ZoneInfo(common_context["user_timezone_name"])
        context["payment_rows"] = [
            {
                "payment": payment,
                "created_times": dual_timezone_display(payment.created_at, user_tz),
                "updated_times": dual_timezone_display(payment.updated_at, user_tz),
            }
            for payment in context["payments"]
        ]
        context.update(common_context)
        return context


class PaymentCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "hotel/payment_form.html"
    success_url = reverse_lazy("payment_list")
    raise_exception = True


class PaymentUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "hotel/payment_form.html"
    success_url = reverse_lazy("payment_list")
    raise_exception = True


class PaymentDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Payment
    template_name = "hotel/confirm_delete.html"
    success_url = reverse_lazy("payment_list")
    raise_exception = True
