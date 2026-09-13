from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _safe_zoneinfo(value: str):
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, PermissionError):
        return None


def get_user_timezone(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, "client_profile", None) or getattr(
            request.user, "employee_profile", None
        )
        if profile and profile.timezone and profile.timezone.strip():
            tz = _safe_zoneinfo(profile.timezone.strip())
            if tz:
                return tz

    session_tz = request.session.get("user_timezone")
    if session_tz and str(session_tz).strip():
        tz = _safe_zoneinfo(str(session_tz).strip())
        if tz:
            return tz

    header_tz = request.headers.get("X-Timezone") or request.META.get("HTTP_X_TIMEZONE")
    if header_tz and str(header_tz).strip():
        tz = _safe_zoneinfo(str(header_tz).strip())
        if tz:
            return tz

    return ZoneInfo("Europe/Minsk")
