import pytest
from django.contrib.auth.hashers import identify_hasher
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
    assert client.get("/api/me/").data["email"] == "alice@example.test"
    client.post("/api/auth/logout/")
    assert client.get("/api/me/").status_code == 403
    csrf = client.get("/api/auth/csrf/").data["csrfToken"]
    assert client.post("/api/auth/login/", {"email":"ALICE@EXAMPLE.TEST","password":"Correct horse battery staple 42"}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code == 200
    assert client.patch("/api/me/", {"display_name":"Alice A.","public_id":"hacker"}, format="json").data["public_id"] == "alice"


@pytest.mark.django_db
def test_search_is_exact_limited_and_never_leaks_email():
    alice = User.objects.create_user("alice@example.test", "alice", "Alice", "long-password-123")
    User.objects.create_user("bob-secret@example.test", "bobby", "Bob", "long-password-123")
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
