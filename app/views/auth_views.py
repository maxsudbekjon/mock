
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from app.serializers import (
    UserRegistrationSerializer,
    ProfileUpdateSerializer,
    UserSerializer,
LoginSerializer,
)
from app.models import User
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Authentication'])
class RegisterView(generics.CreateAPIView):
    """
    Minimal registration - faqat username va password
    POST /api/auth/register

    Body: {
        "username":"Ozodbek"
        "password": "securepass123",
        "password_confirm": "securepass123"
    }
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # User yaratish
        user = serializer.save()

        # JWT token yaratish
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Registration successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Authentication'])
class LoginView(APIView):
    """
    User login
    POST /api/user/login
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Username orqali user qidirish
        try:
            user = User.objects.get(username=username.lower())
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Password tekshirish
        if not user.check_password(password):
            return Response({
                'error': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'error': 'User account is disabled'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # JWT token
        refresh = RefreshToken.for_user(user)

        # Last login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

@extend_schema(tags=['Authentication'])
class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Get va Update profile
    GET /api/auth/profile - profil ko'rish
    PUT/PATCH /api/auth/profile - profil yangilash
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        """Profile yangilash"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # ProfileUpdateSerializer ishlatamiz
        serializer = ProfileUpdateSerializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # To'liq user ma'lumotini qaytaramiz
        return Response(UserSerializer(instance).data)






