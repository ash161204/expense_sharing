import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def enable_db(db):
    """Let every test use the (in-memory) test database."""


@pytest.fixture(autouse=True)
def fast_passwords(settings):
    """Real password hashing is slow on purpose; tests don't need that."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def goa(api):
    """The assignment's example: Mohit (1), Rahul (2) and Ankit (3) in the group "Goa Trip"."""
    for name in ["Mohit", "Rahul", "Ankit"]:
        api.post("/api/users", {"name": name})
    api.post("/api/groups", {"name": "Goa Trip"})
    for user_id in [1, 2, 3]:
        api.post("/api/groups/1/members", {"user_id": user_id})
    return "/api/groups/1"
