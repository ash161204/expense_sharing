"""Demo data, so an evaluator can log in and click around straight away: python manage.py seed

It only adds data to an empty database, so it is safe to run on every start (Docker does).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from ledger.models import Group, User
from ledger.serializers import ExpenseInput
from ledger.services import create_expense

PASSWORD = "demo1234"  # the same for every demo user
ADMIN_USERNAME, ADMIN_PASSWORD = "admin", "admin1234"


def add_expense(group, data):
    """Goes through the same checks as POST /expenses."""
    serializer = ExpenseInput(data=data, context={"group": group})
    serializer.is_valid(raise_exception=True)
    create_expense(group, serializer.validated_data)


class Command(BaseCommand):
    help = "Adds an admin login, 4 demo users and 2 groups with expenses (only into an empty database)."

    def handle(self, *args, **options):
        Admin = get_user_model()  # Django's own user table, used only by the admin panel
        if not Admin.objects.filter(username=ADMIN_USERNAME).exists():
            Admin.objects.create_superuser(ADMIN_USERNAME, password=ADMIN_PASSWORD)

        if User.objects.exists():
            self.stdout.write("The database already has users, so no demo data was added.")
        else:
            self.add_demo_data()

        self.stdout.write(f"App login: Mohit / {PASSWORD} (also Rahul, Ankit, Priya). Admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

    def add_demo_data(self):
        mohit, rahul, ankit, priya = [
            User.objects.create(name=name, password=make_password(PASSWORD)) for name in ["Mohit", "Rahul", "Ankit", "Priya"]
        ]

        # Group 1 is the assignment's example, so the README's requests give the README's answers.
        goa = Group.objects.create(name="Goa Trip")
        goa.members.add(mohit, rahul, ankit)
        add_expense(goa, {"description": "Dinner", "amount": "1200", "payers": [{"user_id": mohit.id, "amount": "1200"}]})

        # Group 2 shows the extras: an item split, two payers, a split between some members, and a settlement.
        mumbai = Group.objects.create(name="Mumbai Weekend")
        mumbai.members.add(mohit, rahul, ankit, priya)
        add_expense(mumbai, {
            "description": "Beach shack lunch",
            "amount": "1500",
            "payers": [{"user_id": rahul.id, "amount": "1500"}],
            "split_type": "itemized",
            "items": [
                {"name": "Pizza", "amount": "600", "shared_by": [mohit.id, rahul.id]},
                {"name": "Beer", "amount": "400", "shared_by": [ankit.id]},
                {"name": "Fries", "amount": "500", "shared_by": [mohit.id, rahul.id, ankit.id, priya.id]},
            ],
        })
        add_expense(mumbai, {
            "description": "Hotel",
            "amount": "8000",
            "payers": [{"user_id": mohit.id, "amount": "5000"}, {"user_id": priya.id, "amount": "3000"}],
        })
        add_expense(mumbai, {
            "description": "Cab to the airport",
            "amount": "900",
            "payers": [{"user_id": ankit.id, "amount": "900"}],
            "participant_ids": [rahul.id, ankit.id, priya.id],
        })
        mumbai.settlements.create(from_user=ankit, to_user=mohit, amount_paise=100000)  # ₹1000
        self.stdout.write("Demo data added: Goa Trip and Mumbai Weekend.")
