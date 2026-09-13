import pytest
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from hotel.utils import _safe_zoneinfo, get_user_timezone


@pytest.mark.django_db
@pytest.mark.parametrize(
    "profile_tz,session_tz,header_tz,expected",
    [
        ("Europe/Vilnius", "Europe/Riga", "Europe/Warsaw", "Europe/Vilnius"),
        ("   ", "Europe/Riga", "Europe/Warsaw", "Europe/Riga"),
        (None, "", "Europe/Warsaw", "Europe/Warsaw"),
        (None, None, None, "Europe/Minsk"),
    ],
)
def test_get_user_timezone_priority_chain(
    profile_tz, session_tz, header_tz, expected, django_user_model, db
):
    rf = RequestFactory()
    request = rf.get("/")
    if header_tz:
        request.META["HTTP_X_TIMEZONE"] = header_tz
    request.session = {}
    if session_tz is not None:
        request.session["user_timezone"] = session_tz

    user = django_user_model.objects.create_user(username="u1", password="pass12345")

    if profile_tz is not None:
        client_profile = user.client_profile
        client_profile.timezone = profile_tz
        client_profile.save(update_fields=["timezone"])
        user.refresh_from_db()
    else:
        user.client_profile.delete()
        user = django_user_model.objects.get(pk=user.pk)

    request.user = user

    tz = get_user_timezone(request)
    assert isinstance(tz, ZoneInfo)
    assert str(tz) == expected


@pytest.mark.parametrize("bad_tz", ["", "Invalid/Timezone", "  "])
def test_safe_zoneinfo_returns_none_for_invalid(bad_tz):
    assert _safe_zoneinfo(bad_tz) is None


def test_get_user_timezone_anonymous_defaults():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    request.session = {}
    tz = get_user_timezone(request)
    assert str(tz) == "Europe/Minsk"
