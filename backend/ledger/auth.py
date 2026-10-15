"""Simple login: sign up or log in with a name and password, and get a token back."""
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import exceptions, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import make_token
from .models import User
from .serializers import UserSerializer


class LoginInput(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    password = serializers.CharField(min_length=4, max_length=128)


def logged_in(user, status=200):
    return Response({"token": make_token(user), "user": UserSerializer(user).data}, status=status)


class Signup(APIView):
    serializer_class = LoginInput  # for Swagger

    def post(self, request):
        serializer = LoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        name, password = serializer.validated_data["name"], serializer.validated_data["password"]

        user = User.objects.filter(name__iexact=name).first()
        if user and user.password:
            raise exceptions.ValidationError({"name": ["This name is already taken."]})
        if user is None:
            user = User(name=name)
        user.password = make_password(password)  # also lets a friend-added user claim their name
        user.save()
        return logged_in(user, status=201)


class Login(APIView):
    serializer_class = LoginInput

    def post(self, request):
        serializer = LoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(name__iexact=serializer.validated_data["name"]).first()
        if not user or not check_password(serializer.validated_data["password"], user.password):
            raise exceptions.ValidationError({"non_field_errors": ["Wrong name or password."]})
        return logged_in(user)


class Me(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        return Response(UserSerializer(request.user).data)
