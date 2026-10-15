"""The assistant's workflow. Plain functions, no LLM: they decide what to ask next and do all the maths.

A draft has the same shape as an expense request (see ledger.serializers.ExpenseInput), so a finished
draft can be validated and saved exactly like an expense typed into the form.
"""
import re
from decimal import Decimal, InvalidOperation

from ledger.money import rupees, split_equally


def start_draft(draft, members):
    """An empty draft (split between everyone) with whatever the browser sent back filled in."""
    empty = {"description": "", "amount": "", "subtotal": "", "payers": [], "items": [], "participant_ids": [m.id for m in members]}
    return {**empty, **(draft or {})}


def clean(amount):
    """"₹1,200.50" -> "1200.50". The word "rest" is kept: finish() works out how much that is."""
    if (amount or "").strip().lower() == "rest":
        return "rest"
    return re.sub(r"[^0-9.]", "", amount or "")


def to_decimal(amount):
    try:
        return Decimal(amount)
    except InvalidOperation:
        return Decimal(0)


def same_item(a, b):
    """"fries" matches "FRIES (LARGE)"."""
    return a.lower() in b.lower() or b.lower() in a.lower()


def merge(draft, found, members, from_receipt=False):
    """Adds what the LLM found to the draft. Names become user ids and amounts are cleaned up."""
    ids = {member.name: member.id for member in members}
    if from_receipt:  # a receipt can't say who paid or who had what, so never take a guess from it
        found = {**found, "who_had_what": [], "payers": []}

    def people(names):
        return list(ids.values()) if "everyone" in names else [ids[name] for name in names]

    if found["description"] and not draft["description"]:  # keep the first title; the user can edit it
        draft["description"] = found["description"]
    if found["total"]:
        draft["amount"] = clean(found["total"])
    if found["subtotal"]:
        draft["subtotal"] = clean(found["subtotal"])
    if found["items"]:
        draft["items"] = [{"name": item["name"], "amount": clean(item["amount"]), "shared_by": []} for item in found["items"]]
    for entry in found["who_had_what"] or []:  # in order, so "everything" first and exceptions after
        for item in draft["items"]:
            if entry["item"].lower() == "everything" or same_item(item["name"], entry["item"]):
                item["shared_by"] = people(entry["people"])
    if found["split_between"]:
        draft["participant_ids"] = people(found["split_between"])
    for payer in found["payers"] or []:  # added to earlier payers: "I paid 1000" ... "Ankit paid the rest"
        if payer["person"] != "everyone":
            user_id = ids[payer["person"]]
            others = [p for p in draft["payers"] if p["user_id"] != user_id]
            draft["payers"] = others + [{"user_id": user_id, "amount": clean(payer["amount"])}]
    return draft


def items_total(draft):
    return sum(to_decimal(item["amount"]) for item in draft["items"])


def items_match_subtotal(draft):
    """A receipt's items should add up to the subtotal printed on it (if it has one)."""
    return not (draft["subtotal"] and draft["items"]) or to_decimal(draft["subtotal"]) == items_total(draft)


def next_question(draft):
    """The first thing still missing, as a fixed question. None means nothing is missing."""
    if not draft["amount"] and not draft["items"]:
        return "What did you spend on? Type it, 📷 scan the bill, or 🎤 speak."
    if not items_match_subtotal(draft):
        return f"The items add up to {items_total(draft)} but the receipt's subtotal is {draft['subtotal']}. Please fix the items (Edit draft)."
    unassigned = [item["name"] for item in draft["items"] if not item["shared_by"]]
    if unassigned:
        return f"Who had what? ({', '.join(unassigned)}) For example: \"pizza: me and Rahul, fries: everyone\"."
    if not draft["payers"]:
        return "Who paid?"
    if len(draft["payers"]) > 1 and not all(payer["amount"] for payer in draft["payers"]):
        return "How much did each person pay?"
    if not draft["description"]:
        return "What should we call this expense?"
    return None


def finish(draft):
    """Fills in what we can work out ourselves: the split type, tax/service charges and payers' amounts."""
    draft["split_type"] = "itemized" if draft["items"] else "equal"
    if draft["items"]:
        bought = items_total(draft)
        total = to_decimal(draft["amount"]) or bought
        if total > bought:  # tax or service charge on the receipt: shared by everyone on the bill
            everyone_on_bill = sorted({user_id for item in draft["items"] for user_id in item["shared_by"]})
            draft["items"].append({"name": "Tax & charges", "amount": str(total - bought), "shared_by": everyone_on_bill})
        draft["amount"] = str(total)
    else:
        del draft["items"]  # an equal split has no items (an empty list would fail validation)
    for payer in draft["payers"]:
        if payer["amount"] == "rest":  # "Ankit paid the rest" = total minus what the others paid
            paid_by_others = sum(to_decimal(p["amount"]) for p in draft["payers"] if p is not payer)
            payer["amount"] = str(to_decimal(draft["amount"]) - paid_by_others)
    if len(draft["payers"]) == 1:
        draft["payers"][0]["amount"] = draft["amount"]
    return draft


def preview_shares(expense, members):
    """Each person's share, worked out the same way create_expense saves it. `expense` is validated ExpenseInput data."""
    if expense["split_type"] == "equal":
        shares = split_equally(expense["amount"], expense["participant_ids"])
    else:
        shares = {}
        for item in expense["items"]:
            for user_id, amount in split_equally(item["amount"], item["shared_by"]).items():
                shares[user_id] = shares.get(user_id, 0) + amount
    names = {member.id: member.name for member in members}
    return [{"user_id": user_id, "name": names[user_id], "amount": rupees(amount)} for user_id, amount in shares.items()]
