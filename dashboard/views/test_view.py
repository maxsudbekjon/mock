from django.template.context_processors import request

from dashboard.serializers import TestSerializer
from rest_framework import viewsets, filters
from dashboard.custom_permission import IsTeacherOrAdminOrReadOnly
from app.models import Test
from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=["Tests"]
)
class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [IsTeacherOrAdminOrReadOnly]  # Custom permission

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'difficulty_level']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.role in ['admin', 'teacher']:
            return Test.objects.all()

        return Test.objects.filter(is_published=True)

    @extend_schema(
        summary="Yangi Test yaratish",
        description="Faqat Admin yoki Teacher test yarata oladi.",
        request=TestSerializer,
        responses={201: TestSerializer}
    )
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)