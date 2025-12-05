from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from app.models import TestAttempt, Test, ListeningQuestion, ListeningAnswer
from app.serializers import TestAttemptSerializer, TestAttemptListSerializer, SubmitListeningAnswerSerializer, \
    ListeningAnswerSerializer, BulkListeningAnswersSerializer


@extend_schema(tags=['student listening answer'])
class TestAttemptViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        user = self.request.user

        # Student faqat o'zini ko'radi
        if user.role == 'student':
            return TestAttempt.objects.filter(user=user).select_related('test', 'user')

        # Teacher/Admin barchasini ko'radi
        return TestAttempt.objects.all().select_related('test', 'user')

    def get_serializer_class(self):
        if self.action == 'list':
            return TestAttemptListSerializer
        return TestAttemptSerializer

    @extend_schema(
        summary="Yangi test boshlash",
        description="Student yangi test topshirishni boshlaydi",
        request={'application/json': {'type': 'object', 'properties': {'test_id': {'type': 'integer'}}}},
        responses={201: TestAttemptSerializer}
    )
    @action(detail=False, methods=['post'], url_path='start-test')
    def start_test(self, request):
        """
        POST /api/attempts/start-test/
        Body: {"test_id": 1}
        """
        test_id = request.data.get('test_id')

        if not test_id:
            return Response(
                {"error": "test_id majburiy!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Test mavjudligini tekshirish
        try:
            test = Test.objects.get(id=test_id, is_published=True)
        except Test.DoesNotExist:
            return Response(
                {"error": "Test topilmadi yoki hali publish qilinmagan!"},
                status=status.HTTP_404_NOT_FOUND
            )

        # IP address olish
        ip_address = request.META.get('REMOTE_ADDR')

        # Yangi attempt yaratish
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            ip_address=ip_address
        )

        return Response(
            TestAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Listening javob yuborish (bitta)",
        description="Bitta listening savolga javob yuborish",
        request=SubmitListeningAnswerSerializer,
        responses={201: ListeningAnswerSerializer}
    )
    @action(detail=True, methods=['post'], url_path='submit-listening-answer')
    def submit_listening_answer(self, request, pk=None):
        """
        POST /api/attempts/{attempt_id}/submit-listening-answer/
        Body: {
            "question_id": 5,
            "user_answer": "London",
            "time_spent": 45
        }
        """
        attempt = self.get_object()

        # Faqat o'z attemptiga javob yuborishi mumkin
        if attempt.user != request.user:
            return Response(
                {"error": "Bu sizning attemptingiz emas!"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Tugallangan testga javob yuborib bo'lmaydi
        if attempt.status == 'completed':
            return Response(
                {"error": "Test allaqachon tugallangan!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmitListeningAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        user_answer = serializer.validated_data['user_answer']
        time_spent = serializer.validated_data.get('time_spent', 0)

        # Savol tekshirish
        try:
            question = ListeningQuestion.objects.get(
                id=question_id,
                section__test=attempt.test
            )
        except ListeningQuestion.DoesNotExist:
            return Response(
                {"error": "Savol topilmadi yoki bu testga tegishli emas!"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Javobni saqlash yoki yangilash
        answer, created = ListeningAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'user_answer': user_answer,
                'time_spent': time_spent,
            }
        )

        # Javobni tekshirish
        answer.check_answer()

        return Response(
            ListeningAnswerSerializer(answer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @extend_schema(
        summary="Ko'p listening javoblarni yuborish",
        description="Bir nechta listening javoblarni bittada yuborish",
        request=BulkListeningAnswersSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'], url_path='submit-listening-answers-bulk')
    def submit_listening_answers_bulk(self, request, pk=None):
        """
        POST /api/attempts/{attempt_id}/submit-listening-answers-bulk/
        Body: {
            "answers": [
                {"question_id": 1, "user_answer": "A", "time_spent": 30},
                {"question_id": 2, "user_answer": "London", "time_spent": 45},
                {"question_id": 3, "user_answer": "C", "time_spent": 25}
            ]
        }
        """
        attempt = self.get_object()

        if attempt.user != request.user:
            return Response(
                {"error": "Bu sizning attemptingiz emas!"},
                status=status.HTTP_403_FORBIDDEN
            )

        if attempt.status == 'completed':
            return Response(
                {"error": "Test allaqachon tugallangan!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BulkListeningAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data['answers']
        question_ids = [ans['question_id'] for ans in answers_data]

        # Barcha savollar mavjud va testga tegishli ekanligini tekshirish
        questions = ListeningQuestion.objects.filter(
            id__in=question_ids,
            section__test=attempt.test
        )

        if questions.count() != len(question_ids):
            return Response(
                {"error": "Ba'zi savollar topilmadi yoki testga tegishli emas!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Bulk create/update
        saved_count = 0
        with transaction.atomic():
            for ans_data in answers_data:
                answer, created = ListeningAnswer.objects.update_or_create(
                    attempt=attempt,
                    question_id=ans_data['question_id'],
                    defaults={
                        'user_answer': ans_data['user_answer'],
                        'time_spent': ans_data.get('time_spent', 0),
                    }
                )
                answer.check_answer()
                saved_count += 1

        return Response(
            {"message": f"{saved_count} ta javob saqlandi va tekshirildi!"},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Listening testini tugatish",
        description="Listening qismini tugatish va ball hisobi"
    )
    @action(detail=True, methods=['post'], url_path='complete-listening')
    def complete_listening(self, request, pk=None):
        """
        POST /api/attempts/{attempt_id}/complete-listening/
        """
        attempt = self.get_object()

        if attempt.user != request.user:
            return Response(
                {"error": "Bu sizning attemptingiz emas!"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Listening javoblarni qayta tekshirish
        with transaction.atomic():
            answers = attempt.listening_answers.select_related('question')
            correct_count = 0

            for answer in answers:
                answer.check_answer()
                if answer.is_correct:
                    correct_count += 1

            # IELTS Listening band score hisoblash
            attempt.listening_score = self._calculate_listening_band(correct_count)
            attempt.save()

            # Overall score yangilash (agar barcha qismlar tugallangan bo'lsa)
            attempt.calculate_overall_score()

        return Response(
            {
                "message": "Listening qismi tugallandi!",
                "correct_answers": correct_count,
                "total_questions": answers.count(),
                "listening_score": float(attempt.listening_score)
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Testni butunlay tugatish",
        description="Barcha qismlarni tugatish va yakuniy ball"
    )
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_test(self, request, pk=None):
        """
        POST /api/attempts/{attempt_id}/complete/
        """
        attempt = self.get_object()

        if attempt.user != request.user:
            return Response(
                {"error": "Bu sizning attemptingiz emas!"},
                status=status.HTTP_403_FORBIDDEN
            )

        if attempt.status == 'completed':
            return Response(
                {"error": "Test allaqachon tugallangan!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Listening
            listening_answers = attempt.listening_answers.select_related('question')
            listening_correct = sum(1 for ans in listening_answers if ans.check_answer())
            if listening_answers.exists():
                attempt.listening_score = self._calculate_listening_band(listening_correct)

            # Status va vaqt yangilash
            attempt.status = 'completed'
            attempt.completed_at = timezone.now()
            attempt.save()

            # Overall score hisoblash
            attempt.calculate_overall_score()

        return Response(
            TestAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Natijalarni ko'rish",
        description="Tugallangan test natijalarini batafsil ko'rish"
    )
    @action(detail=True, methods=['get'], url_path='results')
    def get_results(self, request, pk=None):
        """
        GET /api/attempts/{attempt_id}/results/
        """
        attempt = self.get_object()

        if attempt.user != request.user and request.user.role == 'student':
            return Response(
                {"error": "Bu sizning attemptingiz emas!"},
                status=status.HTTP_403_FORBIDDEN
            )

        if attempt.status != 'completed':
            return Response(
                {"error": "Test hali tugallanmagan!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            TestAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Mening attemptlarim",
        description="Foydalanuvchining barcha attemptlari"
    )
    @action(detail=False, methods=['get'], url_path='my-attempts')
    def my_attempts(self, request):
        """
        GET /api/attempts/my-attempts/
        """
        attempts = TestAttempt.objects.filter(
            user=request.user
        ).select_related('test').order_by('-started_at')

        serializer = TestAttemptListSerializer(attempts, many=True)
        return Response(serializer.data)

    def _calculate_listening_band(self, correct_answers):
        """IELTS Listening band score formula (40 savollik)"""
        band_mapping = {
            40: 9.0, 39: 8.5, 38: 8.5, 37: 8.0, 36: 8.0,
            35: 7.5, 34: 7.5, 33: 7.0, 32: 7.0, 31: 6.5,
            30: 6.5, 29: 6.5, 28: 6.0, 27: 6.0, 26: 6.0,
            25: 5.5, 24: 5.5, 23: 5.5, 22: 5.0, 21: 5.0,
            20: 5.0, 19: 4.5, 18: 4.5, 17: 4.5, 16: 4.0,
            15: 4.0, 14: 3.5, 13: 3.5, 12: 3.0, 11: 3.0,
            10: 2.5, 9: 2.5, 8: 2.0, 7: 2.0, 6: 2.0,
        }
        return band_mapping.get(correct_answers, 1.0)