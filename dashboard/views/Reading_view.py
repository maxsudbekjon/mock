# views.py
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from app.models import ReadingPassage, ReadingQuestion, Test
from dashboard.serializers import (
    ReadingPassageSerializer,
    ReadingPassageListSerializer,
    ReadingPassageCreateUpdateSerializer,
    ReadingQuestionSerializer,
    ReadingQuestionListSerializer,
    TestReadingOverviewSerializer
)
from dashboard.custom_permission import IsTeacherOrAdminOrReadOnly
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(tags=['Reading_passage crud'])
class ReadingPassageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Reading Passages

    Teachers: Full CRUD access
    Students: Read-only access
    """
    queryset = ReadingPassage.objects.all().select_related('test').prefetch_related('questions')
    permission_classes = [IsTeacherOrAdminOrReadOnly]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ReadingPassageListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ReadingPassageCreateUpdateSerializer
        return ReadingPassageSerializer

    def get_queryset(self):
        """Filter passages by test_id if provided"""
        queryset = super().get_queryset()
        test_id = self.request.query_params.get('test_id')

        if test_id:
            queryset = queryset.filter(test_id=test_id)

        return queryset.order_by('passage_number')

    def create(self, request, *args, **kwargs):
        """Create a new reading passage"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return full passage data
        output_serializer = ReadingPassageSerializer(serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """Update reading passage"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return full passage data
        output_serializer = ReadingPassageSerializer(serializer.instance)
        return Response(output_serializer.data)

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get all questions for a specific passage"""
        passage = self.get_object()
        questions = passage.questions.all().order_by('question_number')

        # Show different data based on user role
        if request.user.role == 'teacher' or request.user.role == 'admin':
            serializer = ReadingQuestionSerializer(questions, many=True)
        else:
            serializer = ReadingQuestionListSerializer(questions, many=True)

        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='test_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Test ID to get all passages',
                required=True
            )
        ],
        responses={
            200: TestReadingOverviewSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT
        }
    )
    @action(detail=False, methods=['get'])
    def by_test(self, request):
        """Get all passages for a specific test with overview"""
        test_id = request.query_params.get('test_id')

        if not test_id:
            return Response(
                {'error': 'test_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test = get_object_or_404(Test, pk=test_id)
        serializer = TestReadingOverviewSerializer(test)
        return Response(serializer.data)


@extend_schema(tags=['Reading question crud'])
class ReadingQuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Reading Questions

    Teachers: Full CRUD access
    Students: Read-only access (without answers)
    """
    queryset = ReadingQuestion.objects.all().select_related('passage')
    permission_classes = [IsTeacherOrAdminOrReadOnly]

    def get_serializer_class(self):
        """Return appropriate serializer based on user role"""
        if self.request.user.role == 'teacher' or self.request.user.role == 'admin':
            return ReadingQuestionSerializer
        return ReadingQuestionListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='passage_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter questions by passage ID',
                required=False
            ),
            OpenApiParameter(
                name='test_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter questions by test ID',
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all questions with optional filtering by passage_id or test_id"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=ReadingQuestionSerializer,
        responses={
            201: ReadingQuestionSerializer,
            400: OpenApiTypes.OBJECT
        },
        description="Create a single reading question"
    )
    def create(self, request, *args, **kwargs):
        """Create a single question"""
        return super().create(request, *args, **kwargs)


    def get_queryset(self):
        """Filter questions by passage_id or test_id if provided"""
        queryset = super().get_queryset()
        passage_id = self.request.query_params.get('passage_id')
        test_id = self.request.query_params.get('test_id')

        if passage_id:
            queryset = queryset.filter(passage_id=passage_id)

        if test_id:
            queryset = queryset.filter(passage__test_id=test_id)

        return queryset.order_by('question_number')

    @extend_schema(
        request=ReadingQuestionSerializer(many=True),
        responses={
            201: ReadingQuestionSerializer(many=True),
            400: OpenApiTypes.OBJECT
        },
        description="Create multiple reading questions at once for a passage"
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple questions at once for a passage"""
        if not isinstance(request.data, list):
            return Response(
                {'error': 'Expected a list of questions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReadingQuestionSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='answer',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='User answer to check',
                required=True
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT
        }
    )
    @action(detail=True, methods=['get'])
    def check_answer(self, request, pk=None):
        """Check if provided answer is correct (for practice mode)"""
        question = self.get_object()
        user_answer = request.query_params.get('answer', '').strip()

        if not user_answer:
            return Response(
                {'error': 'Answer parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_correct = user_answer.lower() == question.correct_answer.lower()

        response_data = {
            'is_correct': is_correct,
            'points': question.points if is_correct else 0
        }

        # Show correct answer and explanation only to teachers
        if request.user.role == 'teacher' or request.user.role == 'admin':
            response_data['correct_answer'] = question.correct_answer
            # response_data['explanation'] = question.explanation

        return Response(response_data)

