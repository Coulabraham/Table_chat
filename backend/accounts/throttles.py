from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class EmailActionThrottle(SimpleRateThrottle):
    scope = "email_action"

    def get_cache_key(self, request, view):
        email = ""
        if request.user and request.user.is_authenticated:
            email = request.user.email
        elif isinstance(request.data, dict):
            email = str(request.data.get("email", "")).strip().lower()
        ident = self.get_ident(request)
        digest = self.cache_format % {"scope": self.scope, "ident": f"{ident}:{email}"}
        return digest
