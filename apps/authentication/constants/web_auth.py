"""Web authentication route patterns and cookie names."""

# Guest-only routes — authenticated users are redirected to their dashboard.
IT_GUEST_ROUTE_PREFIXES = (
    "/it/login",
    "/it/signup",
)

FACULTY_GUEST_ROUTE_PREFIXES = (
    "/faculty/login",
    "/faculty/signup",
)

WEB_GUEST_ROUTE_PREFIXES = IT_GUEST_ROUTE_PREFIXES + FACULTY_GUEST_ROUTE_PREFIXES

# Routes that must never be cached by the browser.
IT_SENSITIVE_ROUTE_PREFIXES = (
    "/it/login",
    "/it/signup",
    "/it/dashboard",
    "/jobseeker/",
    "/recruiter/",
    "/auth/logout",
    "/auth/session",
    "/auth/token",
    "/logout",
)

FACULTY_SENSITIVE_ROUTE_PREFIXES = (
    "/faculty/login",
    "/faculty/signup",
    "/professor/",
    "/college/",
)

WEB_SENSITIVE_ROUTE_PREFIXES = (
    IT_SENSITIVE_ROUTE_PREFIXES
    + FACULTY_SENSITIVE_ROUTE_PREFIXES
    + (
        "/auth/forgot-password",
        "/auth/reset-password",
        "/auth/verify-email",
    )
)
