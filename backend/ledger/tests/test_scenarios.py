"""The three scenarios from 01_db_design.md, run through the API."""

DINNER = {"description": "Dinner", "amount": "1200", "payers": [{"user_id": 1, "amount": "1200"}]}

LUNCH = {
    "description": "Beach shack lunch",
    "amount": "1500",
    "payers": [{"user_id": 2, "amount": "1500"}],
    "split_type": "itemized",
    "items": [
        {"name": "Pizza", "amount": "600", "shared_by": [1, 2]},
        {"name": "Beer", "amount": "400", "shared_by": [3]},
        {"name": "Fries", "amount": "500", "shared_by": [1, 2, 3]},
    ],
}

HOTEL = {
    "description": "Hotel",
    "amount": "9000",
    "payers": [{"user_id": 1, "amount": "6000"}, {"user_id": 3, "amount": "3000"}],
    "split_type": "itemized",
    "items": [
        {"name": "Room A", "amount": "5000", "shared_by": [1, 2]},
        {"name": "Room B", "amount": "4000", "shared_by": [3]},
    ],
}


def amounts(rows):
    return [row["amount"] for row in rows]


def test_scenario_1_equal_split_then_settlement(api, goa):
    response = api.post(f"{goa}/expenses", DINNER)
    assert response.status_code == 201
    assert amounts(response.json()["splits"]) == ["400.00", "400.00", "400.00"]

    assert api.get(f"{goa}/balances").json()["owes"] == {
        "Rahul": {"owes": {"Mohit": "400.00"}},
        "Ankit": {"owes": {"Mohit": "400.00"}},
    }

    response = api.post(f"{goa}/settlements", {"from_user_id": 2, "to_user_id": 1, "amount": "400"})
    assert response.status_code == 201
    assert api.get(f"{goa}/balances").json()["owes"] == {"Ankit": {"owes": {"Mohit": "400.00"}}}


def test_scenario_2_item_split(api, goa):
    response = api.post(f"{goa}/expenses", LUNCH)
    assert response.status_code == 201
    assert amounts(response.json()["splits"]) == ["466.67", "466.67", "566.66"]
    fries = response.json()["items"][2]
    assert amounts(fries["shared_by"]) == ["166.67", "166.67", "166.66"]


def test_scenario_3_two_payers_and_everything_combined(api, goa):
    api.post(f"{goa}/expenses", DINNER)
    api.post(f"{goa}/settlements", {"from_user_id": 2, "to_user_id": 1, "amount": "400"})  # right after dinner
    api.post(f"{goa}/expenses", LUNCH)
    response = api.post(f"{goa}/expenses", HOTEL)
    assert response.status_code == 201

    balances = api.get(f"{goa}/balances").json()
    assert [member["net"] for member in balances["members"]] == ["3433.33", "-1466.67", "-1966.66"]
    assert balances["owes"] == {
        "Rahul": {"owes": {"Mohit": "1466.67"}},
        "Ankit": {"owes": {"Mohit": "1966.66"}},
    }

    history = api.get(f"{goa}/expenses").json()
    assert [expense["description"] for expense in history] == ["Hotel", "Beach shack lunch", "Dinner"]
