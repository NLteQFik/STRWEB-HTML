from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.views import View

from ..services import get_external_data, get_weather_data


def weather_api_proxy(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden(
            "Доступ к внешним API разрешен только авторизованным клиентам"
        )
    return JsonResponse(get_weather_data())


weather_api_proxy.login_url = "login"


class CurrencyApiProxyView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponseForbidden(
                "Доступ к внешним API разрешен только авторизованным клиентам"
            )
        return JsonResponse(get_external_data())
