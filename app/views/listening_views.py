from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from app.models import (
    Test, TestAttempt, ListeningSection, ListeningQuestion, ListeningAnswer
)
from app.serializers import (
    ListeningSectionSerializer,
    ListeningAnswerSubmitSerializer,
    ListeningAnswerSerializer,
    ListeningAnswerForTeacherSerializer,
    ListeningGradeSerializer,
    ListeningBulkGradeSerializer,
    ListeningStudentResultSerializer,
)

TAG_STUDENT = 'Listening - Student'
TAG_TEACHER = 'Listening - Teacher'


# class ListeningSectionListView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     @extend_schema(
#         tags=[TAG_STUDENT],
#         summary="Testning barcha listening bo'limlarini olish",
#         description="Berilgan test ID bo'yicha listening sectionlar va savollarni qaytaradi.",
#         responses={200: ListeningSectionSerializer(many=True)}
#     )
#     def get(self, request, test_id):
#         test = get_object_or_404(Test, id=test_id, is_published=True)
#         sections = ListeningSection.objects.filter(test=test).prefetch_related('questions')
#
#         if not sections.exists():
#             return Response({'error': 'No listening sections found'}, status=status.HTTP_404_NOT_FOUND)
#
#         serializer = ListeningSectionSerializer(sections, many=True)
#         return Response({
#             'test_id': test.id,
#             'test_title': test.title,
#             'total_sections': sections.count(),
#             'sections': serializer.data
#         })


class ListeningAnswerSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_STUDENT],
        summary="Bitta javob yuborish",
        request=ListeningAnswerSubmitSerializer,
        responses={200: ListeningAnswerSerializer}
    )
    def post(self, request):
        # ... (eski kod o'zgarishsiz qoladi)
        attempt_id = request.data.get('attempt_id')
        if not attempt_id:
            return Response({'error': 'attempt_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user, status='in_progress')

        serializer = ListeningAnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        user_answer = serializer.validated_data['user_answer']
        question = get_object_or_404(ListeningQuestion, id=question_id)

        answer, created = ListeningAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'user_answer': user_answer,
                'is_correct': False,
                'graded_at': None,
                'graded_by': None
            }
        )

        return Response({
            'message': 'Answer submitted successfully',
            'answer': ListeningAnswerSerializer(answer).data,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ListeningBulkAnswerSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_STUDENT],
        summary="Ko'p javoblarni bir vaqtda yuborish",
        description="Format: {'attempt_id': 1, 'answers': [{'question_id': 1, 'user_answer': 'A'}]}",
        request=None,  # Yoki bu yerga maxsus Bulk Serializer yozib qo'yish mumkin
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        # ... (eski kod o'zgarishsiz qoladi)
        attempt_id = request.data.get('attempt_id')
        answers_data = request.data.get('answers', [])

        if not attempt_id or not answers_data:
            return Response({'error': 'required fields missing'}, status=status.HTTP_400_BAD_REQUEST)

        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user, status='in_progress')
        saved_answers = []
        errors = []

        for answer_data in answers_data:
            try:
                question_id = answer_data.get('question_id')
                user_answer = answer_data.get('user_answer', '').strip()
                if not question_id: continue

                question = ListeningQuestion.objects.get(id=question_id)
                answer, _ = ListeningAnswer.objects.update_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={'user_answer': user_answer, 'is_correct': False}
                )
                saved_answers.append(ListeningAnswerSerializer(answer).data)
            except Exception as e:
                errors.append({'question_id': question_id, 'error': str(e)})

        return Response({
            'message': f'{len(saved_answers)} answers saved',
            'saved_answers': saved_answers,
            'errors': errors
        })


# ========================================
# TEACHER VIEWS
# ========================================

class TeacherPendingListeningView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_TEACHER],
        summary="Baholash kutilayotgan javoblar",
        responses={200: ListeningAnswerForTeacherSerializer(many=True)}
    )
    def get(self, request):
        if not request.user.is_teacher and not request.user.is_admin_user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        pending_answers = ListeningAnswer.objects.filter(graded_at__isnull=True) \
            .select_related('attempt__user', 'question__section__test').order_by('submitted_at')

        # ... (Data formatlash logikasi) ...
        # Qisqartirib yozildi, asosiy logika sizda bor
        return Response({'total_pending': pending_answers.count(), 'data': '...'})


class TeacherGradeListeningAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_TEACHER],
        summary="Bitta javobni baholash",
        request=ListeningGradeSerializer,
        responses={200: ListeningAnswerForTeacherSerializer}
    )
    def post(self, request):
        if not request.user.is_teacher and not request.user.is_admin_user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ListeningGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ... (Baholash logikasi) ...
        answer = get_object_or_404(ListeningAnswer, id=serializer.validated_data['answer_id'])
        answer.is_correct = serializer.validated_data['is_correct']
        answer.teacher_comment = serializer.validated_data.get('teacher_comment', '')
        answer.graded_by = request.user
        answer.graded_at = timezone.now()
        answer.save()

        return Response({
            'message': 'Graded',
            'answer': ListeningAnswerForTeacherSerializer(answer).data
        })


class TeacherBulkGradeListeningView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_TEACHER],
        summary="Bir nechta javobni baholash (Bulk)",
        request=ListeningBulkGradeSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        if not request.user.is_teacher and not request.user.is_admin_user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # ... (Bulk baholash logikasi) ...
        return Response({'message': 'Bulk graded'})


class TeacherStudentListeningDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_TEACHER],
        summary="Studentning to'liq natijalarini ko'rish",
        responses={200: ListeningAnswerForTeacherSerializer(many=True)}
    )
    def get(self, request, attempt_id):
        # ... (Logika) ...
        return Response({'message': 'Details'})


# ========================================
# STUDENT RESULT VIEWS
# ========================================

class StudentListeningResultView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_STUDENT],
        summary="Student o'z natijasini ko'rishi",
        parameters=[
            OpenApiParameter(name='attempt_id', description='Test urinish ID si', required=True, type=int),
        ],
        responses={200: ListeningStudentResultSerializer(many=True)}
    )
    def get(self, request):
        attempt_id = request.query_params.get('attempt_id')
        if not attempt_id:
            return Response({'error': 'attempt_id required'}, status=status.HTTP_400_BAD_REQUEST)

        # ... (Natijalarni hisoblash logikasi) ...
        return Response({'result': '...'})


class StudentListeningStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[TAG_STUDENT],
        summary="Baholash statusini tekshirish",
        parameters=[
            OpenApiParameter(name='attempt_id', description='Test urinish ID si', required=True, type=int),
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        attempt_id = request.query_params.get('attempt_id')
        # ... (Status tekshirish logikasi) ...
        return Response({'status': '...'})