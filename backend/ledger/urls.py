from django.urls import path

from . import auth, views

urlpatterns = [
    path("auth/signup", auth.Signup.as_view()),
    path("auth/login", auth.Login.as_view()),
    path("auth/me", auth.Me.as_view()),
    path("users", views.UserList.as_view()),
    path("groups", views.GroupList.as_view()),
    path("groups/<int:group_id>", views.GroupDetail.as_view()),
    path("groups/<int:group_id>/members", views.GroupMembers.as_view()),
    path("groups/<int:group_id>/expenses", views.GroupExpenses.as_view()),
    path("groups/<int:group_id>/balances", views.GroupBalances.as_view()),
    path("groups/<int:group_id>/settlements", views.GroupSettlements.as_view()),
    path("groups/<int:group_id>/pdf", views.GroupPdf.as_view()),
]
