import pytest
from django.db import IntegrityError, transaction

from ledger.models import Expense, ExpenseSplit, Settlement


def expense(amount="300", payers=None, **extra):
    """Builds an expense request; by default Mohit pays and it is split equally."""
    payers = payers or [{"user_id": 1, "amount": amount}]
    return {"description": "Snacks", "amount": amount, "payers": payers, **extra}


# ---------- users, groups, members ----------

def test_user_names_are_unique_ignoring_case(api):
    assert api.post("/api/users", {"name": "Mohit"}).status_code == 201
    assert api.post("/api/users", {"name": "mohit"}).status_code == 400


def test_blank_user_name_is_rejected(api):
    assert api.post("/api/users", {"name": "   "}).status_code == 400


def test_add_member_errors(api, goa):
    assert api.post(f"{goa}/members", {"user_id": 1}).status_code == 400   # already a member
    assert api.post(f"{goa}/members", {"user_id": 99}).status_code == 400  # no such user
    assert api.post("/api/groups/99/members", {"user_id": 1}).status_code == 404


def test_lists(api, goa):
    assert len(api.get("/api/users").json()) == 3
    assert api.get("/api/groups/1").json()["name"] == "Goa Trip"
    assert [m["name"] for m in api.get(f"{goa}/members").json()] == ["Mohit", "Rahul", "Ankit"]


# ---------- expenses ----------

@pytest.mark.parametrize("amount", [0, -5, "10.005", "abc", "1,200", None, True])
def test_bad_amounts_are_rejected(api, goa, amount):
    response = api.post(f"{goa}/expenses", expense(amount=amount))
    assert response.status_code == 400


def test_payer_must_be_in_the_group(api, goa):
    api.post("/api/users", {"name": "Zoya"})  # user 4, not in the group
    response = api.post(f"{goa}/expenses", expense(payers=[{"user_id": 4, "amount": "300"}]))
    assert response.status_code == 400
    assert "payers" in response.json()


def test_payers_must_add_up(api, goa):
    payers = [{"user_id": 1, "amount": "100"}, {"user_id": 2, "amount": "100"}]
    assert api.post(f"{goa}/expenses", expense(payers=payers)).status_code == 400


def test_same_payer_twice_is_rejected(api, goa):
    payers = [{"user_id": 1, "amount": "150"}, {"user_id": 1, "amount": "150"}]
    assert api.post(f"{goa}/expenses", expense(payers=payers)).status_code == 400


def test_participants_can_be_chosen(api, goa):
    response = api.post(f"{goa}/expenses", expense(participant_ids=[2, 3]))
    assert response.status_code == 201
    assert [split["name"] for split in response.json()["splits"]] == ["Rahul", "Ankit"]


def test_participants_must_be_in_the_group(api, goa):
    assert api.post(f"{goa}/expenses", expense(participant_ids=[1, 9])).status_code == 400


def test_amount_too_small_to_split(api, goa):
    assert api.post(f"{goa}/expenses", expense(amount="0.02")).status_code == 400


def test_itemized_needs_items(api, goa):
    assert api.post(f"{goa}/expenses", expense(split_type="itemized")).status_code == 400


def test_items_must_add_up(api, goa):
    items = [{"name": "Tea", "amount": "100", "shared_by": [1]}]
    assert api.post(f"{goa}/expenses", expense(split_type="itemized", items=items)).status_code == 400


def test_item_too_small_to_split(api, goa):
    items = [{"name": "Mint", "amount": "0.02", "shared_by": [1, 2, 3]}, {"name": "Tea", "amount": "299.98", "shared_by": [1]}]
    assert api.post(f"{goa}/expenses", expense(split_type="itemized", items=items)).status_code == 400


def test_missing_group_is_404(api):
    assert api.post("/api/groups/99/expenses", expense()).status_code == 404


# ---------- settlements ----------

def test_cannot_settle_more_than_owed(api, goa):
    api.post(f"{goa}/expenses", expense(amount="1200"))  # Rahul owes Mohit 400
    response = api.post(f"{goa}/settlements", {"from_user_id": 2, "to_user_id": 1, "amount": "500"})
    assert response.status_code == 400
    assert response.json()["amount"] == ["You can settle at most 400.00 here."]


def test_cannot_settle_with_yourself(api, goa):
    assert api.post(f"{goa}/settlements", {"from_user_id": 1, "to_user_id": 1, "amount": "1"}).status_code == 400


def test_settlement_users_must_be_members(api, goa):
    assert api.post(f"{goa}/settlements", {"from_user_id": 9, "to_user_id": 1, "amount": "1"}).status_code == 400


def test_settlement_history(api, goa):
    api.post(f"{goa}/expenses", expense(amount="1200"))
    api.post(f"{goa}/settlements", {"from_user_id": 2, "to_user_id": 1, "amount": "100"})
    assert api.get(f"{goa}/settlements").json()[0]["amount"] == "100.00"


# ---------- the database protects itself too ----------

def test_database_rejects_settling_with_yourself(goa):
    with pytest.raises(IntegrityError), transaction.atomic():
        Settlement.objects.create(group_id=1, from_user_id=1, to_user_id=1, amount_paise=100)


def test_expense_is_saved_all_or_nothing(api, goa, monkeypatch):
    def broken_create(**kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(ExpenseSplit.objects, "create", broken_create)
    with pytest.raises(RuntimeError):
        api.post(f"{goa}/expenses", expense())
    assert Expense.objects.count() == 0  # the expense row was rolled back too
