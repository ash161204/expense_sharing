import pytest

from ledger.tests.conftest import api, enable_db, fast_passwords, goa  # noqa: F401  (reuse the shared fixtures)


@pytest.fixture
def mohit(api, goa):  # noqa: F811
    """Logged in as Mohit, a member of the Goa Trip group."""
    token = api.post("/api/auth/signup", {"name": "Mohit", "password": "secret1"}).json()["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return f"{goa}/assistant"


def found(**fields):
    """A fake LLM answer: everything empty unless given."""
    empty = {"description": None, "total": None, "subtotal": None, "items": [], "who_had_what": [], "split_between": [], "payers": []}
    return {**empty, **fields}
