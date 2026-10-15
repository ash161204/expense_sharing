from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Group, User
from .money import rupees, who_owes_whom
from .pdf import group_pdf
from .serializers import (
    AddMemberInput, BalanceSerializer, ExpenseInput, ExpenseSerializer,
    GroupSerializer, SettlementInput, SettlementSerializer, UserSerializer,
)
from .services import calculate_balances, create_expense


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupList(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class GroupDetail(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    lookup_url_kwarg = "group_id"


class GroupMembers(APIView):
    serializer_class = UserSerializer  # tells Swagger what the response looks like

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        return Response(UserSerializer(group.members.all(), many=True).data)

    @extend_schema(request=AddMemberInput, responses=UserSerializer)
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        serializer = AddMemberInput(data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user_id"]
        group.members.add(user)
        return Response(UserSerializer(user).data, status=201)


class GroupExpenses(APIView):
    serializer_class = ExpenseSerializer

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        expenses = group.expenses.prefetch_related("payments__user", "splits__user", "items__shares__user")
        return Response(ExpenseSerializer(expenses, many=True).data)

    @extend_schema(request=ExpenseInput, responses=ExpenseSerializer)
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        serializer = ExpenseInput(data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)
        expense = create_expense(group, serializer.validated_data)
        return Response(ExpenseSerializer(expense).data, status=201)


class GroupBalances(APIView):
    serializer_class = BalanceSerializer

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        balances = calculate_balances(group)

        net_by_name = {balance["name"]: balance["net"] for balance in balances.values()}
        owes = {}
        for debtor, creditor, amount in who_owes_whom(net_by_name):
            owes.setdefault(debtor, {"owes": {}})
            owes[debtor]["owes"][creditor] = rupees(amount)

        return Response({"members": BalanceSerializer(balances.values(), many=True).data, "owes": owes})


class GroupSettlements(APIView):
    serializer_class = SettlementSerializer

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        settlements = group.settlements.select_related("from_user", "to_user")
        return Response(SettlementSerializer(settlements, many=True).data)

    @extend_schema(request=SettlementInput, responses=SettlementSerializer)
    @transaction.atomic  # the balance check and the insert happen together
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        serializer = SettlementInput(data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)
        settlement = group.settlements.create(
            from_user_id=serializer.validated_data["from_user_id"],
            to_user_id=serializer.validated_data["to_user_id"],
            amount_paise=serializer.validated_data["amount"],
        )
        return Response(SettlementSerializer(settlement).data, status=201)


class PdfRenderer(BaseRenderer):
    """Lets clients that ask for application/pdf (like Swagger) call the PDF endpoint."""
    media_type = "application/pdf"
    format = "pdf"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class GroupPdf(APIView):
    renderer_classes = [JSONRenderer, PdfRenderer]  # JSON first, so a 404 still comes back as JSON

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        filename = slugify(group.name) or "group"
        return HttpResponse(
            group_pdf(group),
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
        )
