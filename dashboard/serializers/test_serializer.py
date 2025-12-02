from rest_framework import serializers
from app.models import Test




class TestSerializer(serializers.ModelSerializer):
    # User obyektini string (username) sifatida qaytarish yoki shunchaki ID.
    # Read_only bo'lishi shart, chunki biz buni request.user dan olamiz
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Test
        fields = [
            'id',
            'title',
            'description',
            'difficulty_level',
            'is_published',
            'created_by',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
