from django.contrib import admin

from .models import (
    Expense, ExpenseItem, ExpenseItemShare, ExpensePayment, ExpenseSplit,
    Group, GroupMember, Settlement, User,
)

# Lets you browse and delete rows at /admin/ (handy while testing).
admin.site.register([
    User, Group, GroupMember, Expense, ExpensePayment, ExpenseSplit, ExpenseItem, ExpenseItemShare, Settlement,
])
