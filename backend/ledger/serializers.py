from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Group, User
from .money import rupees
from .services import calculate_balances


class MoneyField(serializers.DecimalField):
    """JSON uses rupees ("1200.50"). Our Python code uses whole paise (120050)."""

    def __init__(self, **kwargs):
        super().__init__(max_digits=12, decimal_places=2, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)  # checks it is a number with at most 2 decimals
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return int(value * 100)

    def to_representation(self, paise):
        return rupees(paise)


def member_ids(group):
    return set(group.members.values_list("id", flat=True))


def check_people(user_ids, members, field):
    """Each person may be listed only once and must be a member of the group."""
    if len(user_ids) != len(set(user_ids)):
        raise serializers.ValidationError({field: "A person is listed more than once."})
    outsiders = sorted(set(user_ids) - members)
    if outsiders:
        raise serializers.ValidationError({field: f"Users {outsiders} are not members of this group."})


# ---------- Users and groups ----------

class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        validators=[UniqueValidator(User.objects.all(), lookup="iexact", message="This name is already taken.")],
    )

    class Meta:
        model = User
        fields = ["id", "name", "created_at"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "created_at"]


class AddMemberInput(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # gives us the User object

    def validate_user_id(self, user):
        if user.id in member_ids(self.context["group"]):
            raise serializers.ValidationError("User is already a member of this group.")
        return user


# ---------- Expenses ----------

class PayerInput(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = MoneyField()


class ItemInput(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    amount = MoneyField()
    shared_by = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class ExpenseInput(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    amount = MoneyField()
    payers = PayerInput(many=True, allow_empty=False)
    split_type = serializers.ChoiceField(choices=["equal", "itemized"], default="equal")
    participant_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=False)
    items = ItemInput(many=True, required=False, allow_empty=False)

    def validate(self, data):
        members = member_ids(self.context["group"])
        self.check_payers(data, members)
        if data["split_type"] == "equal":
            self.check_equal_split(data, members)
        else:
            self.check_items(data, members)
        return data

    def check_payers(self, data, members):
        check_people([payer["user_id"] for payer in data["payers"]], members, "payers")
        if sum(payer["amount"] for payer in data["payers"]) != data["amount"]:
            raise serializers.ValidationError({"payers": "Payer amounts must add up to the expense amount."})

    def check_equal_split(self, data, members):
        if "participant_ids" not in data:  # nobody chosen: split between the whole group
            data["participant_ids"] = sorted(members)
        check_people(data["participant_ids"], members, "participant_ids")
        if data["amount"] < len(data["participant_ids"]):
            raise serializers.ValidationError({"amount": "Amount is too small to split between these people."})

    def check_items(self, data, members):
        items = data.get("items")
        if not items:
            raise serializers.ValidationError({"items": "An itemized expense needs at least one item."})
        if sum(item["amount"] for item in items) != data["amount"]:
            raise serializers.ValidationError({"items": "Item amounts must add up to the expense amount."})
        for item in items:
            check_people(item["shared_by"], members, "items")
            if item["amount"] < len(item["shared_by"]):
                raise serializers.ValidationError({"items": f"{item['name']} is too small to split."})


class ShareSerializer(serializers.Serializer):
    """A person and an amount. Used for payers, splits and item shares."""
    user_id = serializers.IntegerField()
    name = serializers.CharField(source="user.name")
    amount = MoneyField(source="amount_paise")


class ItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = MoneyField(source="amount_paise")
    shared_by = ShareSerializer(source="shares", many=True)


class ExpenseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    amount = MoneyField(source="amount_paise")
    split_type = serializers.CharField()
    payers = ShareSerializer(source="payments", many=True)
    splits = ShareSerializer(many=True)
    items = ItemSerializer(many=True)
    created_at = serializers.DateTimeField()


# ---------- Balances and settlements ----------

class BalanceSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    paid = MoneyField()
    share = MoneyField()
    net = MoneyField()


class SettlementInput(serializers.Serializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()
    amount = MoneyField()

    def validate(self, data):
        group = self.context["group"]
        sender, receiver = data["from_user_id"], data["to_user_id"]
        if sender == receiver:
            raise serializers.ValidationError("You cannot settle with yourself.")
        check_people([sender, receiver], member_ids(group), "users")

        balances = calculate_balances(group)
        most_allowed = max(0, min(-balances[sender]["net"], balances[receiver]["net"]))
        if data["amount"] > most_allowed:
            raise serializers.ValidationError({"amount": f"You can settle at most {rupees(most_allowed)} here."})
        return data


class SettlementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    from_user_id = serializers.IntegerField()
    from_user = serializers.CharField(source="from_user.name")
    to_user_id = serializers.IntegerField()
    to_user = serializers.CharField(source="to_user.name")
    amount = MoneyField(source="amount_paise")
    created_at = serializers.DateTimeField()
