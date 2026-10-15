"""The demo data (python manage.py seed) and the PDF export."""
from django.contrib.auth import get_user_model
from django.core.management import call_command


def test_seed_adds_the_demo_data_once(api):
    call_command("seed")
    call_command("seed")  # safe to run again: nothing is added twice

    assert [group["name"] for group in api.get("/api/groups").json()] == ["Goa Trip", "Mumbai Weekend"]
    assert api.get("/api/groups/1/balances").json()["owes"] == {  # the README's example
        "Rahul": {"owes": {"Mohit": "400.00"}},
        "Ankit": {"owes": {"Mohit": "400.00"}},
    }
    assert api.get("/api/groups/2/balances").json()["owes"] == {
        "Rahul": {"owes": {"Mohit": "1225.00"}},
        "Ankit": {"owes": {"Mohit": "350.00", "Priya": "575.00"}},
    }
    assert api.post("/api/auth/login", {"name": "Mohit", "password": "demo1234"}).status_code == 200
    assert get_user_model().objects.get(username="admin").check_password("admin1234")


def test_pdf_export(api):
    call_command("seed")
    response = api.get("/api/groups/2/pdf")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'attachment; filename="mumbai-weekend.pdf"'
    assert response.content.startswith(b"%PDF")

    assert api.get("/api/groups/2/pdf", HTTP_ACCEPT="application/pdf").status_code == 200  # what Swagger sends


def test_pdf_of_an_empty_group_and_a_missing_group(api, goa):
    assert api.get(f"{goa}/pdf").content.startswith(b"%PDF")
    assert api.get("/api/groups/99/pdf").status_code == 404
