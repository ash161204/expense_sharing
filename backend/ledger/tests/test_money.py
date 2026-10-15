from hypothesis import given
from hypothesis import strategies as st

from ledger.money import rupees, split_equally, who_owes_whom


def test_rupees():
    assert rupees(120050) == "1200.50"
    assert rupees(0) == "0.00"
    assert rupees(-146667) == "-1466.67"


def test_split_equally_gives_leftover_paise_to_lowest_ids():
    assert split_equally(10000, [3, 1, 2]) == {1: 3334, 2: 3333, 3: 3333}


def test_who_owes_whom_assignment_example():
    payments = who_owes_whom({"Mohit": 80000, "Rahul": -40000, "Ankit": -40000})
    assert payments == [("Rahul", "Mohit", 40000), ("Ankit", "Mohit", 40000)]


@given(
    amount=st.integers(min_value=50, max_value=10**10),
    user_ids=st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=50, unique=True),
)
def test_split_equally_always_adds_up(amount, user_ids):
    shares = split_equally(amount, user_ids)
    assert sum(shares.values()) == amount                     # nothing lost or invented
    assert max(shares.values()) - min(shares.values()) <= 1   # fair to the paisa


@given(st.lists(st.integers(min_value=-10**9, max_value=10**9), min_size=1, max_size=20))
def test_who_owes_whom_settles_everyone(values):
    net = {person: value for person, value in enumerate(values)}
    net["last"] = -sum(values)  # balances in a group always add up to zero
    for debtor, creditor, amount in who_owes_whom(net):
        net[debtor] += amount
        net[creditor] -= amount
    assert all(value == 0 for value in net.values())
