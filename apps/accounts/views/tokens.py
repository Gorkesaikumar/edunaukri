from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.authentication.api.schema import jwt_obtain_schema, jwt_refresh_schema
from apps.authentication.permissions.throttles import (
    BruteForceIPThrottle,
    LoginEndpointThrottle,
    LoginIPThrottle,
    TokenRefreshThrottle,
)
from apps.accounts.serializers.tokens import (
    AdminTokenObtainPairSerializer,
    CollegeTokenObtainPairSerializer,
    DomainTokenRefreshSerializer,
    FacultyTokenObtainPairSerializer,
    ITTokenObtainPairSerializer,
    ProfessorTokenObtainPairSerializer,
)


@jwt_obtain_schema
class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]


@jwt_obtain_schema
class ITTokenObtainPairView(TokenObtainPairView):
    serializer_class = ITTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]


@jwt_obtain_schema
class FacultyTokenObtainPairView(TokenObtainPairView):
    serializer_class = FacultyTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]


@jwt_obtain_schema
class ProfessorTokenObtainPairView(TokenObtainPairView):
    serializer_class = ProfessorTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]


@jwt_obtain_schema
class CollegeTokenObtainPairView(TokenObtainPairView):
    serializer_class = CollegeTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]


@jwt_refresh_schema
class DomainTokenRefreshView(TokenRefreshView):
    serializer_class = DomainTokenRefreshSerializer
    permission_classes = [AllowAny]
    throttle_classes = [BruteForceIPThrottle, TokenRefreshThrottle]
