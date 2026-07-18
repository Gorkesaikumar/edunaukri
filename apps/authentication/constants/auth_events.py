"""Canonical authentication and session event types."""

AUTH_LOGIN_SUCCESS = "auth.login.success"
AUTH_LOGIN_FAILURE = "auth.login.failure"
AUTH_LOGOUT = "auth.logout"
AUTH_TOKEN_REFRESH = "auth.token.refresh"
AUTH_TOKEN_REUSE_DETECTED = "auth.token.reuse_detected"
AUTH_PASSWORD_CHANGED = "auth.password.changed"
AUTH_LOGOUT_ALL_DEVICES = "auth.logout.all_devices"
AUTH_NEW_DEVICE_LOGIN = "auth.login.new_device"
AUTH_SESSION_REVOKED = "auth.session.revoked"
AUTH_UNAUTHORIZED_UUID_ACCESS = "auth.route.unauthorized_uuid"

AUTH_EVENT_TYPES = frozenset(
    {
        AUTH_LOGIN_SUCCESS,
        AUTH_LOGIN_FAILURE,
        AUTH_LOGOUT,
        AUTH_TOKEN_REFRESH,
        AUTH_TOKEN_REUSE_DETECTED,
        AUTH_PASSWORD_CHANGED,
        AUTH_LOGOUT_ALL_DEVICES,
        AUTH_NEW_DEVICE_LOGIN,
        AUTH_SESSION_REVOKED,
        AUTH_UNAUTHORIZED_UUID_ACCESS,
    }
)
