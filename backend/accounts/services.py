import hashlib
import logging
import secrets
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone

from .models import AccountSession, AccountToken, User, UserBlock

logger = logging.getLogger(__name__)


class InvalidAccountToken(Exception):
    pass


def _token_digest(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _issue_token(user, kind, lifetime_seconds):
    secret = secrets.token_urlsafe(32)
    token = AccountToken.objects.create(
        user=user,
        kind=kind,
        token_hash=_token_digest(secret),
        email_snapshot=user.email,
        expires_at=timezone.now() + timezone.timedelta(seconds=lifetime_seconds),
    )
    return f"{token.id.hex}.{secret}"


def _parse_token(raw_token):
    try:
        selector, secret = raw_token.split(".", 1)
        return uuid.UUID(hex=selector), secret
    except (AttributeError, ValueError):
        raise InvalidAccountToken from None


def _email_link(path, token):
    return f"{settings.APP_BASE_URL.rstrip('/')}/{path}#token={token}"


def send_verification_email(user):
    now = timezone.now()
    user.account_tokens.filter(kind=AccountToken.Kind.EMAIL_VERIFICATION, used_at__isnull=True).update(used_at=now)
    token = _issue_token(user, AccountToken.Kind.EMAIL_VERIFICATION, settings.EMAIL_VERIFICATION_TTL_SECONDS)
    try:
        send_mail(
            "Vérifiez votre adresse TableChat",
            "Bonjour,\n\nVérifiez votre adresse en ouvrant ce lien :\n"
            f"{_email_link('verify-email', token)}\n\n"
            "Ce lien est temporaire et utilisable une seule fois.\n",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Échec d'envoi de l'email de vérification (%s).", type(exc).__name__)
        return False
    return True


@transaction.atomic
def verify_email(raw_token):
    selector, secret = _parse_token(raw_token)
    try:
        token = AccountToken.objects.select_for_update().select_related("user").get(
            pk=selector, kind=AccountToken.Kind.EMAIL_VERIFICATION
        )
    except AccountToken.DoesNotExist:
        raise InvalidAccountToken from None
    now = timezone.now()
    if (
        token.used_at
        or token.expires_at <= now
        or token.email_snapshot != token.user.email
        or not secrets.compare_digest(token.token_hash, _token_digest(secret))
    ):
        raise InvalidAccountToken
    token.used_at = now
    token.save(update_fields=("used_at",))
    token.user.email_verified_at = now
    token.user.save(update_fields=("email_verified_at",))
    token.user.account_tokens.filter(kind=AccountToken.Kind.EMAIL_VERIFICATION, used_at__isnull=True).exclude(pk=token.pk).update(used_at=now)
    return token.user


def request_password_reset(email):
    user = User.objects.filter(email=User.objects.normalize_email(email).lower(), is_active=True).first()
    if user is None:
        return
    now = timezone.now()
    user.account_tokens.filter(kind=AccountToken.Kind.PASSWORD_RESET, used_at__isnull=True).update(used_at=now)
    token = _issue_token(user, AccountToken.Kind.PASSWORD_RESET, settings.PASSWORD_RESET_TTL_SECONDS)
    try:
        send_mail(
            "Réinitialisez votre mot de passe TableChat",
            "Bonjour,\n\nChoisissez un nouveau mot de passe avec ce lien :\n"
            f"{_email_link('reset-password', token)}\n\n"
            "Ce lien est temporaire et utilisable une seule fois. Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Échec d'envoi de l'email de récupération (%s).", type(exc).__name__)


def session_group_name(session_key):
    return f"session_{hashlib.sha256(session_key.encode('utf-8')).hexdigest()}"


def notify_revoked_sessions(session_keys):
    channel_layer = get_channel_layer()
    for session_key in session_keys:
        async_to_sync(channel_layer.group_send)(session_group_name(session_key), {"type": "session.revoked"})


def revoke_user_sessions(user, *, exclude_session_key=None):
    keys = [key for key in user_session_keys(user) if key != exclude_session_key]
    if keys:
        Session.objects.filter(session_key__in=keys).delete()
        notify_revoked_sessions(keys)
    return len(keys)


def user_session_keys(user):
    keys = set(user.account_sessions.values_list("session_id", flat=True))
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        try:
            if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
                keys.add(session.session_key)
        except Exception:
            continue
    return sorted(keys)


def sync_account_sessions(user):
    known = set(user.account_sessions.values_list("session_id", flat=True))
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        if session.session_key in known:
            continue
        try:
            belongs_to_user = str(session.get_decoded().get("_auth_user_id")) == str(user.pk)
        except Exception:
            belongs_to_user = False
        if belongs_to_user:
            AccountSession.objects.get_or_create(
                session=session,
                defaults={
                    "user": user,
                    "description": "Session antérieure (indication)",
                    "user_agent": "",
                    "ip_address": None,
                },
            )


@transaction.atomic
def reset_password(raw_token, new_password):
    selector, secret = _parse_token(raw_token)
    try:
        token = AccountToken.objects.select_for_update().select_related("user").get(
            pk=selector, kind=AccountToken.Kind.PASSWORD_RESET
        )
    except AccountToken.DoesNotExist:
        raise InvalidAccountToken from None
    now = timezone.now()
    if token.used_at or token.expires_at <= now or not secrets.compare_digest(token.token_hash, _token_digest(secret)):
        raise InvalidAccountToken
    password_validation.validate_password(new_password, token.user)
    token.user.set_password(new_password)
    token.user.save(update_fields=("password",))
    token.used_at = now
    token.save(update_fields=("used_at",))
    token.user.account_tokens.filter(kind=AccountToken.Kind.PASSWORD_RESET, used_at__isnull=True).exclude(pk=token.pk).update(used_at=now)
    session_keys = user_session_keys(token.user)
    Session.objects.filter(session_key__in=session_keys).delete()
    transaction.on_commit(lambda: notify_revoked_sessions(session_keys))
    return token.user


def describe_user_agent(user_agent):
    value = user_agent or ""
    if "Android" in value:
        platform = "Android"
    elif "iPhone" in value or "iPad" in value:
        platform = "iPhone ou iPad"
    elif "Windows" in value:
        platform = "Windows"
    elif "Macintosh" in value:
        platform = "macOS"
    elif "Linux" in value:
        platform = "Linux"
    else:
        platform = "Appareil inconnu"
    if "Edg/" in value:
        browser = "Edge"
    elif "Firefox/" in value:
        browser = "Firefox"
    elif "Chrome/" in value or "CriOS/" in value:
        browser = "Chrome"
    elif "Safari/" in value:
        browser = "Safari"
    else:
        browser = "Navigateur inconnu"
    return f"{browser} sur {platform} (indication)"


def track_request_session(request):
    if not request.user.is_authenticated:
        return None
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    session = Session.objects.filter(session_key=session_key).first()
    if session is None:
        request.session.save()
        session = Session.objects.get(session_key=request.session.session_key)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip_address = (forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
    record, created = AccountSession.objects.get_or_create(
        session=session,
        defaults={
            "user": request.user,
            "description": describe_user_agent(user_agent),
            "user_agent": user_agent,
            "ip_address": ip_address,
        },
    )
    if not created:
        changed = []
        for field, value in (
            ("user", request.user),
            ("description", describe_user_agent(user_agent)),
            ("user_agent", user_agent),
            ("ip_address", ip_address),
        ):
            current = getattr(record, f"{field}_id", None) if field == "user" else getattr(record, field)
            expected = value.pk if field == "user" else value
            if current != expected:
                setattr(record, field, value)
                changed.append(field)
        if changed:
            record.save(update_fields=changed)
    return record


def messaging_blocked(user_a, user_b):
    return UserBlock.objects.filter(
        models.Q(blocker=user_a, blocked=user_b) | models.Q(blocker=user_b, blocked=user_a)
    ).exists()
