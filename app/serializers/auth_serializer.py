from django.core.validators import validate_domain_name
from rest_framework import serializers
from app.models import User
from django.contrib.auth.password_validation import  validate_password


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Minimal registration - faqat username va password"""
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)  # password_confirm o'rniga password2

    class Meta:
        model = User
        fields = ['username', 'password', 'password2']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this username already exists")
        if len(value)<3:
            raise serializers.ValidationError("Username must be at least 3 characters")
        return value.lower().strip()

    def validate(self, data):
        """Passwordlar match bo'lishi kerak"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                "password2": "Passwords do not match"
            })
        return data

    def create(self, validated_data):
        """User yaratish"""
        # password2 ni olib tashlaymiz
        validated_data.pop('password2')

        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            role='student',
        )

        return user

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Profile to'ldirish/yangilash"""

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'email'
        ]

    def validate_phone_number(self, value):
        """Phone number format validation (optional)"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format")
        return value


class UserSerializer(serializers.ModelSerializer):
    """User detail serializer"""
    is_profile_complete = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone_number',
            'is_profile_complete', 'created_at'
        ]
        read_only_fields = ['id', 'username', 'role', 'created_at']

    def get_is_profile_complete(self, obj):
        """Profile to'liq to'ldirilganmi?"""
        return bool(
            obj.first_name and
            obj.last_name and
            obj.phone_number
        )




class LoginSerializer(serializers.Serializer):
    """LOgin uchun"""
    username = serializers.CharField()

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Foydalanuvchi paroli"
    )






