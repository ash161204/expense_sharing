from decimal import Decimal


def rupees(paise):
    """Shows paise as rupees: 120050 -> "1200.50", -146667 -> "-1466.67"."""
    return f"{Decimal(paise) / 100:.2f}"


def split_equally(amount, user_ids):
    """Splits an amount (in paise) equally. Leftover paise go to the lowest user ids.

    split_equally(10000, [1, 2, 3]) -> {1: 3334, 2: 3333, 3: 3333}
    """
    share, leftover = divmod(amount, len(user_ids))
    shares = {}
    for position, user_id in enumerate(sorted(user_ids)):
        shares[user_id] = share
        if position < leftover:
            shares[user_id] += 1
    return shares


def who_owes_whom(net_balances):
    """Turns net balances into payments that settle everyone.

    who_owes_whom({"Mohit": 80000, "Rahul": -40000, "Ankit": -40000})
    -> [("Rahul", "Mohit", 40000), ("Ankit", "Mohit", 40000)]
    """
    debts = {person: -net for person, net in net_balances.items() if net < 0}
    credits = {person: net for person, net in net_balances.items() if net > 0}

    payments = []
    for debtor in debts:
        for creditor in credits:
            amount = min(debts[debtor], credits[creditor])
            if amount > 0:
                payments.append((debtor, creditor, amount))
                debts[debtor] -= amount
                credits[creditor] -= amount
    return payments
