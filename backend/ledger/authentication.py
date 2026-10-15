"""Login tokens: the user id signed with SECRET_KEY, so there's no token table.

Kept apart from the views because DRF loads this module while it is still starting up.
"""
from django.core import signing
from rest_framework import authentication, exceptions

from .models import User

TOKEN_DAYS = 30


def make_token(user):
    return signing.dumps(user.id, salt="login")


class TokenAuthentication(authentication.BaseAuthentication):
    """Reads "Authorization: Bearer <token>" and finds the user."""

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None  # not logged in; open endpoints still work
        try:
            user_id = signing.loads(header.removeprefix("Bearer "), salt="login", max_age=TOKEN_DAYS * 24 * 3600)
            return User.objects.get(id=user_id), None
        except (signing.BadSignature, User.DoesNotExist):
            raise exceptions.AuthenticationFailed("Please log in again.")

    def authenticate_header(self, request):
        return "Bearer"  # makes DRF answer 401 (not 403) when you're not logged in
