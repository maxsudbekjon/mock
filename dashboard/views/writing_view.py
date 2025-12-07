from trace import Trace

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from app.models import WritingTask, Test
from dashboard.serializers import (
    WritingTaskSerializer,
    WritingTaskListSerializer,
    WritingTaskDetailSerializer
)
from dashboard.custom_permission import IsTeacherOrAdminOrReadOnly


@extend_schema(tags=['Writing Tasks'])
class WritingTaskViewSet(viewsets.ModelViewSet):
    """
    Writing Task CRUD

    Teacher/Admin: Create, Read, Update, Delete
    Student: Read only
    """
    queryset = WritingTask.objects.all().select_related('test')
    permission_classes = [IsTeacherOrAdminOrReadOnly]

    parser_classes = (MultiPartParser, FormParser)


    def get_serializer_class(self):
        """Role ga qarab serializer tanlash"""
        user = self.request.user

        # Teacher/Admin uchun to'liq serializer
        if user.role in ['teacher', 'admin']:
            return WritingTaskSerializer

        # Student uchun
        if self.action == 'retrieve':
            return WritingTaskDetailSerializer
        return WritingTaskListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='test_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter tasks by test ID',
                required=False
            ),
            OpenApiParameter(
                name='task_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by task type (TASK_1 or TASK_2)',
                required=False,
                enum=['TASK_1', 'TASK_2']  # ← MANA SHU QATOR
            )
        ]
    )

    def list(self, request, *args, **kwargs):
        """..."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'test': {'type': 'integer'},
                    'task_number': {'type': 'integer'},
                    'task_type': {
                        'type': 'string',
                        'enum': ['TASK_1', 'TASK_2']  # ← DROPDOWN
                    },
                    'prompt_text': {'type': 'string'},
                    'image': {'type': 'string', 'format': 'binary'},
                    'word_limit': {'type': 'integer'},
                    'time_suggestion': {'type': 'integer'},
                }
            }
        },
        responses={201: WritingTaskSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


    def get_queryset(self):
        """Filter by test_id or task_type if provided"""
        queryset = super().get_queryset()

        test_id = self.request.query_params.get('test_id')
        task_type = self.request.query_params.get('task_type')

        if test_id:
            queryset = queryset.filter(test_id=test_id)

        if task_type:
            queryset = queryset.filter(task_type=task_type)

        return queryset.order_by('test_id', 'task_number')



    @extend_schema(
        request=WritingTaskSerializer,
        responses={
            200: WritingTaskSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def update(self, request, *args, **kwargs):
        """Writing task ni yangilash"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=WritingTaskSerializer,
        responses={
            200: WritingTaskSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Writing task ni qisman yangilash"""
        return super().partial_update(request, *args, **kwargs)

    # @extend_schema(
    #     parameters=[
    #         OpenApiParameter(
    #             name='test_id',
    #             type=OpenApiTypes.INT,
    #             location=OpenApiParameter.QUERY,
    #             description='Test ID to get its writing tasks',
    #             required=True
    #         )
    #     ]
    # )
    # @action(detail=False, methods=['get'])
    # def by_test(self, request):
    #     """
    #     Bitta testning barcha writing tasklarini olish
    #
    #     GET /writing-tasks/by_test/?test_id=5
    #     """
    #     test_id = request.query_params.get('test_id')
    #
    #     if not test_id:
    #         return Response(
    #             {'error': 'test_id parameter is required'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     # Test mavjudligini tekshirish
    #     test = get_object_or_404(Test, pk=test_id)
    #
    #     # Test ning barcha writing tasklarini olish
    #     tasks = self.get_queryset().filter(test_id=test_id)
    #     serializer = self.get_serializer(tasks, many=True)
    #
    #     return Response({
    #         'test_id': test.id,
    #         'test_title': test.title,
    #         'total_tasks': tasks.count(),
    #         'tasks': serializer.data
    #     })

    @extend_schema(
        request=WritingTaskSerializer(many=True),
        responses={
            201: WritingTaskSerializer(many=True),
            400: OpenApiTypes.OBJECT
        },
        description="Create both tasks for a test at once"
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Bir testning ikkala taskini bir vaqtda yaratish

        POST /writing-tasks/bulk_create/
        [
            {
                "test": 1,
                "task_number": 1,
                "task_type": "TASK_1",
                "prompt_text": "...",
                "word_limit": 150,
                "time_suggestion": 20
            },
            {
                "test": 1,
                "task_number": 2,
                "task_type": "TASK_2",
                "prompt_text": "...",
                "word_limit": 250,
                "time_suggestion": 40
            }
        ]
        """
        if not isinstance(request.data, list):
            return Response(
                {'error': 'Expected a list of tasks'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(request.data) != 2:
            return Response(
                {'error': 'Expected exactly 2 tasks (Task 1 and Task 2)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = WritingTaskSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)