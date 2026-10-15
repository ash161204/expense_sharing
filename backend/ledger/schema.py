"""Tells Swagger about our login token, so /api/docs shows an "Authorize" button."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TokenScheme(OpenApiAuthenticationExtension):
    target_class = "ledger.authentication.TokenAuthentication"
    name = "Token"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer"}
