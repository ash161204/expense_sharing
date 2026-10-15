from types import SimpleNamespace

from assistant.draft import finish, merge, next_question, start_draft
from assistant.tests.conftest import found

MEMBERS = [SimpleNamespace(id=1, name="Mohit"), SimpleNamespace(id=2, name="Rahul"), SimpleNamespace(id=3, name="Ankit")]


def draft(**fields):
    return {**start_draft(None, MEMBERS), **fields}


def item(name, amount, shared_by=()):
    return {"name": name, "amount": amount, "shared_by": list(shared_by)}


# ---------- next_question: the fixed order of questions ----------

def test_questions_come_in_order():
    assert next_question(draft()).startswith("What did you spend on?")
    assert next_question(draft(items=[item("Pizza", "600")])).startswith("Who had what? (Pizza)")
    assert next_question(draft(amount="1200")) == "Who paid?"
    two_payers = [{"user_id": 1, "amount": "600"}, {"user_id": 2, "amount": ""}]
    assert next_question(draft(amount="1200", payers=two_payers)) == "How much did each person pay?"
    one_payer = [{"user_id": 1, "amount": ""}]
    assert next_question(draft(amount="1200", payers=one_payer)) == "What should we call this expense?"
    assert next_question(draft(amount="1200", payers=one_payer, description="Dinner")) is None


def test_items_must_match_the_receipt_subtotal():
    question = next_question(draft(subtotal="694.00", items=[item("Room", "189.00", [1])]))
    assert question.startswith("The items add up to 189.00 but the receipt's subtotal is 694.00")


# ---------- merge: LLM answer -> draft ----------

def test_merge_turns_names_into_ids_and_cleans_amounts():
    answer = found(description="Dinner", total="₹1,200", payers=[{"person": "Mohit", "amount": None}],
                   split_between=["Rahul", "Ankit"])
    result = merge(draft(), answer, MEMBERS)
    assert result["amount"] == "1200"
    assert result["payers"] == [{"user_id": 1, "amount": ""}]
    assert result["participant_ids"] == [2, 3]


def test_everything_then_exceptions():
    bill = draft(items=[item("Pizza", "600"), item("Beer", "400")])
    answer = found(who_had_what=[{"item": "everything", "people": ["everyone"]}, {"item": "beer", "people": ["Ankit"]}])
    result = merge(bill, answer, MEMBERS)
    assert [i["shared_by"] for i in result["items"]] == [[1, 2, 3], [3]]


def test_first_title_is_kept_and_everyone_cannot_pay():
    result = merge(draft(description="Beach lunch"), found(description="Food", payers=[{"person": "everyone", "amount": None}]), MEMBERS)
    assert result["description"] == "Beach lunch"
    assert result["payers"] == []


def test_payers_add_up_across_turns_and_rest_is_kept():
    first = merge(draft(amount="1500"), found(payers=[{"person": "Mohit", "amount": "1,000"}]), MEMBERS)
    second = merge(first, found(payers=[{"person": "Ankit", "amount": "rest"}]), MEMBERS)
    assert second["payers"] == [{"user_id": 1, "amount": "1000"}, {"user_id": 3, "amount": "rest"}]
    assert next_question(second) == "What should we call this expense?"  # "rest" counts as an answer


def test_null_lists_from_the_llm_are_treated_as_empty():
    answer = found(items=None, who_had_what=None, split_between=None, payers=None, total="100")
    assert merge(draft(), answer, MEMBERS)["amount"] == "100"


# ---------- finish: what Django works out itself ----------

def test_tax_and_charges_item_is_added_for_the_people_on_the_bill():
    result = finish(draft(amount="1150", items=[item("Pizza", "600", [1, 2]), item("Beer", "400", [2])],
                          payers=[{"user_id": 1, "amount": ""}]))
    assert result["items"][-1] == {"name": "Tax & charges", "amount": "150", "shared_by": [1, 2]}
    assert result["split_type"] == "itemized"
    assert result["payers"][0]["amount"] == "1150"


def test_rest_is_worked_out_by_django():
    payers = [{"user_id": 1, "amount": "1000"}, {"user_id": 3, "amount": "rest"}]
    result = finish(draft(amount="1500", payers=payers))
    assert result["payers"] == [{"user_id": 1, "amount": "1000"}, {"user_id": 3, "amount": "500"}]


def test_equal_split_has_no_items():
    result = finish(draft(amount="900", payers=[{"user_id": 1, "amount": ""}]))
    assert result["split_type"] == "equal"
    assert "items" not in result
