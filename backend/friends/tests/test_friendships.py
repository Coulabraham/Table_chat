import pytest
from django.core.exceptions import ValidationError
from accounts.models import User
from friends.models import Friendship


@pytest.mark.django_db
def test_self_and_crossed_requests_are_rejected():
    alice = User.objects.create_user(email="a@example.test", display_name="Alice test", password="motdepasse")
    bob = User.objects.create_user(email="b@example.test", display_name="Bob test", password="motdepasse")
    with pytest.raises(ValidationError):
        Friendship.objects.create(requester=alice, addressee=alice)
    Friendship.objects.create(requester=alice, addressee=bob)
    with pytest.raises(ValidationError):
        Friendship.objects.create(requester=bob, addressee=alice)
