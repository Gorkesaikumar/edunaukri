from drf_spectacular.extensions import OpenApiAuthenticationExtension

class DomainJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.jwt.DomainJWTAuthentication"
    name = "DomainJWT"
    match_subclasses = True
    priority = -1

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
