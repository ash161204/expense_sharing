from django.db import transaction
from django.db.models import Sum

from .models import Expense, ExpenseItem, ExpenseItemShare, ExpensePayment, ExpenseSplit, Settlement
from .money import split_equally


@transaction.atomic
def create_expense(group, data):
    """Saves an expense with its payers, items and splits. Either every row is saved or none is."""
    expense = Expense.objects.create(
        group=group,
        description=data["description"],
        amount_paise=data["amount"],
        split_type=data["split_type"],
    )

    for payer in data["payers"]:
        ExpensePayment.objects.create(expense=expense, user_id=payer["user_id"], amount_paise=payer["amount"])

    if data["split_type"] == "equal":
        shares = split_equally(data["amount"], data["participant_ids"])
    else:
        shares = save_items(expense, data["items"])

    for user_id, amount in shares.items():
        ExpenseSplit.objects.create(expense=expense, user_id=user_id, amount_paise=amount)

    return expense


def save_items(expense, items):
    """Saves each item and who shared it. Returns each person's total share of the bill."""
    totals = {}
    for item in items:
        saved_item = ExpenseItem.objects.create(expense=expense, name=item["name"], amount_paise=item["amount"])
        for user_id, amount in split_equally(item["amount"], item["shared_by"]).items():
            ExpenseItemShare.objects.create(item=saved_item, user_id=user_id, amount_paise=amount)
            totals[user_id] = totals.get(user_id, 0) + amount
    return totals


def total_by_user(rows, user_field):
    """Adds up amount_paise per user: {user_id: total}."""
    totals = rows.values(user_field).annotate(total=Sum("amount_paise"))
    return {row[user_field]: row["total"] for row in totals}


def calculate_balances(group):
    """What each member paid, their share and their net balance, all in paise.

    net > 0: the group owes this person money. net < 0: this person owes money.
    """
    paid = total_by_user(ExpensePayment.objects.filter(expense__group=group), "user_id")
    share = total_by_user(ExpenseSplit.objects.filter(expense__group=group), "user_id")
    sent = total_by_user(Settlement.objects.filter(group=group), "from_user_id")
    received = total_by_user(Settlement.objects.filter(group=group), "to_user_id")

    balances = {}
    for user in group.members.all():
        user_paid = paid.get(user.id, 0)
        user_share = share.get(user.id, 0)
        net = user_paid - user_share + sent.get(user.id, 0) - received.get(user.id, 0)
        balances[user.id] = {"user_id": user.id, "name": user.name, "paid": user_paid, "share": user_share, "net": net}
    return balances
