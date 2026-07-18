from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class SearchEndpointThrottle(UserRateThrottle):
    scope = "search"


class SearchAnonThrottle(SimpleRateThrottle):
    scope = "search_anon"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
