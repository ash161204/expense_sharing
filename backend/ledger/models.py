from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


class SplitType(models.TextChoices):
    # Module level (not nested in Expense) so Meta.constraints can reference it.
    EQUAL = "equal", "Equal"
    ITEMIZED = "itemized", "Item-wise"


class User(models.Model):
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=128, blank=True)  # hashed; empty = added by a friend, hasn't signed up
    created_at = models.DateTimeField(auto_now_add=True)

    is_authenticated = True  # lets DRF treat a logged-in User like Django's own user

    class Meta:
        db_table = "users"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(Lower("name"), name="uq_user_name_ci")]

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, through="GroupMember", related_name="expense_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups"
        ordering = ["id"]

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "group_members"
        ordering = ["joined_at", "id"]
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="uq_group_member")]


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="expenses")
    description = models.CharField(max_length=255)
    amount_paise = models.BigIntegerField()
    split_type = models.CharField(max_length=16, choices=SplitType.choices, default=SplitType.EQUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["group", "-created_at"], name="ix_expense_group_created")]
        constraints = [
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_expense_amount_pos"),
            models.CheckConstraint(condition=Q(split_type__in=SplitType.values), name="ck_expense_split_type"),
        ]


class ExpensePayment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="expense_payments")
    amount_paise = models.BigIntegerField()

    class Meta:
        db_table = "expense_payments"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="uq_payment_expense_user"),
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_payment_amount_pos"),
        ]


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="expense_splits")
    amount_paise = models.BigIntegerField()

    class Meta:
        db_table = "expense_splits"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="uq_split_expense_user"),
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_split_amount_pos"),
        ]


class ExpenseItem(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    amount_paise = models.BigIntegerField()

    class Meta:
        db_table = "expense_items"
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_item_amount_pos")]


class ExpenseItemShare(models.Model):
    item = models.ForeignKey(ExpenseItem, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="item_shares")
    amount_paise = models.BigIntegerField()

    class Meta:
        db_table = "expense_item_shares"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["item", "user"], name="uq_item_share_item_user"),
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_item_share_amount_pos"),
        ]


class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="settlements")
    from_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="settlements_sent")
    to_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="settlements_received")
    amount_paise = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settlements"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["group", "-created_at"], name="ix_settlement_group_created")]
        constraints = [
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ck_settlement_amount_pos"),
            models.CheckConstraint(condition=~Q(from_user=F("to_user")), name="ck_settlement_not_self"),
        ]
