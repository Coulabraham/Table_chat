import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User


@pytest.mark.django_db
def test_register_login_profile_and_private_email():
    client = APIClient()
    csrf = client.get("/api/auth/csrf/").data["csrfToken"]
    response = client.post("/api/auth/register/", {"email":"Alice@Example.Test","public_id":"alice","display_name":"Alice","password":"Correct horse battery staple 42"}, format="json", HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 201
    alice = User.objects.get(public_id="alice")
    assert identify_hasher(alice.password).algorithm == "argon2"
    assert response.data["email_verified"] is False
    assert client.get("/api/me/").data["email"] == "alice@example.test"
    client.post("/api/auth/logout/")
    assert client.get("/api/me/").status_code == 403
    csrf = client.get("/api/auth/csrf/").data["csrfToken"]
    assert client.post("/api/auth/login/", {"email":"ALICE@EXAMPLE.TEST","password":"Correct horse battery staple 42"}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code == 200
    assert client.patch("/api/me/", {"display_name":"Alice A.","public_id":"hacker"}, format="json").data["public_id"] == "alice"


@pytest.mark.django_db
@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
def test_registration_can_temporarily_bypass_email_verification():
    client = APIClient()
    response = client.post(
        "/api/auth/register/",
        {
            "email": "tester@example.test",
            "public_id": "tester",
            "display_name": "Tester",
            "password": "long-password-123",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["email_verified"] is True
    assert response.data["verification_email_sent"] is False
    assert User.objects.get(public_id="tester").email_verified_at is not None
    assert len(mail.outbox) == 0

    User.objects.create_user(
        "legacy@example.test",
        "legacy_user",
        "Legacy",
        "long-password-123",
    )
    result = client.get("/api/users/search/?public_id=legacy_user")
    assert result.status_code == 200
    assert [user["public_id"] for user in result.data] == ["legacy_user"]


@pytest.mark.django_db
def test_search_is_exact_limited_and_never_leaks_email():
    alice = User.objects.create_user("alice@example.test", "alice", "Alice", "long-password-123", email_verified_at=timezone.now())
    User.objects.create_user("bob-secret@example.test", "bobby", "Bob", "long-password-123", email_verified_at=timezone.now())
    client = APIClient(); client.force_login(alice)
    assert client.get("/api/users/search/?public_id=bob").data == []
    result = client.get("/api/users/search/?public_id=bobby").data
    assert len(result) == 1 and "email" not in result[0]


@pytest.mark.django_db
def test_csrf_is_required_for_session_authenticated_write():
    user = User.objects.create_user("alice@example.test", "alice", "Alice", "long-password-123")
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.patch("/api/me/", {"display_name":"Changed"}, format="json").status_code == 403
    csrf = client.get("/api/auth/csrf/").data["csrfToken"]
    assert client.patch("/api/me/", {"display_name":"Changed"}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code == 200


@pytest.mark.django_db
def test_login_endpoint_rejects_missing_csrf():
    User.objects.create_user("alice@example.test", "alice", "Alice", "long-password-123")
    client = APIClient(enforce_csrf_checks=True)
    response = client.post("/api/auth/login/", {"email":"alice@example.test","password":"long-password-123"}, format="json")
    assert response.status_code == 403
