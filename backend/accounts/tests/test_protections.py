import re

import pytest
from django.core import mail
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken, User


def extract_token(message):
    return re.search(r"#token=([^\s]+)", message.body).group(1)


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()


@pytest.mark.django_db
def test_email_verification_is_one_time_and_expiring():
    client=APIClient()
    response=client.post("/api/auth/register/",{"email":"verify@example.test","public_id":"verify_user","display_name":"Verify","password":"long-password-123"},format="json")
    assert response.status_code==201 and response.data["email_verified"] is False
    assert len(mail.outbox)==1
    token=extract_token(mail.outbox[0])
    verified=client.post("/api/auth/email/verify/",{"token":token},format="json")
    assert verified.status_code==200 and verified.data["user"]["email_verified"] is True
    assert client.post("/api/auth/email/verify/",{"token":token},format="json").status_code==400

    second=User.objects.create_user("expired@example.test","expired_user","Expired","long-password-123")
    from accounts.services import send_verification_email
    send_verification_email(second)
    expired_token=extract_token(mail.outbox[-1])
    AccountToken.objects.filter(user=second).update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
    assert client.post("/api/auth/email/verify/",{"token":expired_token},format="json").status_code==400

    changed=User.objects.create_user("before@example.test","changed_user","Changed","long-password-123")
    send_verification_email(changed)
    changed_token=extract_token(mail.outbox[-1])
    changed.email="after@example.test";changed.save()
    assert client.post("/api/auth/email/verify/",{"token":changed_token},format="json").status_code==400


@pytest.mark.django_db
def test_verification_resend_is_rate_limited():
    user=User.objects.create_user("resend@example.test","resend_user","Resend","long-password-123")
    client=APIClient();client.force_login(user)
    statuses=[client.post("/api/auth/email/resend/",{},format="json").status_code for _ in range(6)]
    assert statuses[:5]==[200]*5
    assert statuses[5]==429


@pytest.mark.django_db
def test_password_reset_does_not_disclose_account_and_revokes_sessions():
    user=User.objects.create_user("reset@example.test","reset_user","Reset","old-password-123",email_verified_at=timezone.now())
    first=APIClient();second=APIClient();legacy=APIClient()
    first.force_login(user);second.force_login(user);legacy.force_login(user)
    assert first.get("/api/me/").status_code==200
    assert second.get("/api/me/").status_code==200
    assert Session.objects.count()==3

    anonymous=APIClient()
    existing=anonymous.post("/api/auth/password-reset/request/",{"email":"reset@example.test"},format="json")
    missing=anonymous.post("/api/auth/password-reset/request/",{"email":"missing@example.test"},format="json")
    assert existing.status_code==missing.status_code==202
    assert existing.data==missing.data
    assert len(mail.outbox)==1
    token=extract_token(mail.outbox[0])
    changed=anonymous.post("/api/auth/password-reset/confirm/",{"token":token,"new_password":"new-password-456"},format="json")
    assert changed.status_code==200
    user.refresh_from_db()
    assert user.check_password("new-password-456")
    assert Session.objects.count()==0
    assert first.get("/api/me/").status_code==403
    assert second.get("/api/me/").status_code==403
    assert legacy.get("/api/me/").status_code==403
    assert anonymous.post("/api/auth/password-reset/confirm/",{"token":token,"new_password":"another-password-789"},format="json").status_code==400


@pytest.mark.django_db
def test_sessions_can_list_current_and_revoke_another():
    user=User.objects.create_user("sessions@example.test","sessions_user","Sessions","long-password-123",email_verified_at=timezone.now())
    laptop=APIClient();phone=APIClient()
    laptop.force_login(user);phone.force_login(user)
    laptop.get("/api/me/",HTTP_USER_AGENT="Mozilla/5.0 Windows Chrome/120")
    phone.get("/api/me/",HTTP_USER_AGENT="Mozilla/5.0 Android Chrome/120")
    sessions=laptop.get("/api/sessions/").data
    assert len(sessions)==2 and sum(item["current"] for item in sessions)==1
    other=next(item for item in sessions if not item["current"])
    assert laptop.delete(f"/api/sessions/{other['id']}/").status_code==204
    assert phone.get("/api/me/").status_code==403
