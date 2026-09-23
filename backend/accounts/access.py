from django.conf import settings


def email_verification_satisfied(user):
    """Return whether the current deployment lets this user use messaging."""
    return bool(not settings.REQUIRE_EMAIL_VERIFICATION or user.email_verified_at)


def can_use_private_messaging(user):
    """Single access rule shared by the HTTP API and WebSocket consumers."""
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and email_verification_satisfied(user)
    )
