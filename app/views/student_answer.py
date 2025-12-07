# views.py - FINAL VERSION
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from app.models import (
    TestAttempt, ListeningAnswer, ReadingAnswer, WritingSubmission,
    Test, ListeningQuestion, ReadingQuestion, WritingTask, ListeningSection
)
from app.serializers import (
    ListeningSubmitSerializer,
    ReadingSubmitSerializer,
    WritingSubmitSerializer,
    TestAttemptDetailSerializer, TestAttemptListSerializer, GradeAttemptSerializer
)


def check_and_complete_attempt(attempt):
    """Barcha sectionlar submitted bo'lsa, avtomatik completed qilish"""
    if attempt.all_sections_submitted():
        if attempt.status != 'completed':
            attempt.mark_completed()
            return True
    return False


# ==================== LISTENING VIEWSET ====================
@extend_schema(tags=['Listening Submit'])
class ListeningSubmissionViewSet(viewsets.ViewSet):
    """Listening javoblarini boshqarish"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        # Kiruvchi ma'lumotni to'g'ridan-to'g'ri belgilash
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'test_id': {
                        'type': 'integer',
                        'description': 'Boshlanadigan testning ID raqami.'
                    }
                },
                # test_id majburiy ekanligini ko'rsatadi
                'required': ['test_id']
            }
        },
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Listening sectionni boshlash - vaqt limitini olish

        POST /api/listening/start/
        {
            "test_id": 1
        }

        Response:
        {
            "attempt_id": 123,
            "time_limit": 2060,  // Audio duration + 600 sekund
            "audio_duration": 1460,  // Faqat audio
            "extra_time": 600,  // 10 daqiqa
            "started_at": "2025-12-07T10:00:00Z"
        }
        """
        test_id = request.data.get('test_id')
        if not test_id:
            return Response(
                {'error': 'test_id majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test = get_object_or_404(Test, pk=test_id)

        # TestAttempt yaratish yoki olish
        attempt, created = TestAttempt.objects.get_or_create(
            user=request.user,
            test=test,
            defaults={'status': 'in_progress'}
        )

        # Listening allaqachon submitted bo'lsa
        if attempt.listening_submitted:
            return Response(
                {'error': 'Listening allaqachon topshirilgan. Qayta boshlash mumkin emas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Listening start time ni belgilash (faqat birinchi marta)
        if not attempt.listening_started_at:
            attempt.listening_started_at = timezone.now()
            attempt.save(update_fields=['listening_started_at'])

        # Barcha sectionlarning audio durationini yig'ish
        sections = ListeningSection.objects.filter(test=test)
        total_audio_duration = sum(section.audio_duration for section in sections)

        # Time limit = audio + 10 daqiqa
        time_limit = total_audio_duration + 600

        return Response({
            'attempt_id': attempt.id,
            'time_limit': time_limit,
            'audio_duration': total_audio_duration,
            'extra_time': 600,
            'started_at': attempt.listening_started_at,
        })

    @extend_schema(
        request=ListeningSubmitSerializer,
        responses={201: TestAttemptDetailSerializer}
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit(self, request):
        """
        Barcha listening javoblarini yuborish (FAQAT BIR MARTA)

        POST /api/listening/submit/
        {
            "test_id": 1,
            "answers": {"1": "A", "2": "library", ...},
            "time_spent": 2050
        }
        """
        serializer = ListeningSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_id = serializer.validated_data['test_id']
        answers = serializer.validated_data['answers']
        time_spent = serializer.validated_data['time_spent']

        test = get_object_or_404(Test, pk=test_id)

        # Attempt olish
        try:
            attempt = TestAttempt.objects.get(user=request.user, test=test)
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Avval /listening/start/ ni chaqiring'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ ASOSIY CHECK: Allaqachon submitted bo'lsa, REJECT
        if attempt.listening_submitted:
            return Response(
                {'error': 'Listening allaqachon topshirilgan. Qayta yuborib bo\'lmaydi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Test completed bo'lsa
        if attempt.status == 'completed':
            return Response(
                {'error': 'Test allaqachon tugallangan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Questionlarni olish
        questions = ListeningQuestion.objects.filter(
            section__test=test
        ).select_related('section')

        total_questions = questions.count()
        question_map = {str(q.question_number): q for q in questions}

        # Javoblarni saqlash
        answers_to_create = []
        for q_number_str, user_answer in answers.items():
            question = question_map.get(q_number_str)
            if question:
                answers_to_create.append(
                    ListeningAnswer(
                        attempt=attempt,
                        question=question,
                        user_answer=user_answer.strip()
                    )
                )

        # Avvalgilarni o'chirish va yangilarini saqlash
        ListeningAnswer.objects.filter(attempt=attempt).delete()
        if answers_to_create:
            ListeningAnswer.objects.bulk_create(answers_to_create)

        # ✅ Listening ni submitted qilish
        attempt.listening_submitted = True
        attempt.listening_submitted_at = timezone.now()
        attempt.save(update_fields=['listening_submitted', 'listening_submitted_at'])

        # Barcha sectionlar submitted bo'lsa, completed qilish
        auto_completed = check_and_complete_attempt(attempt)

        # Response
        response_data = {
            'message': 'Listening muvaffaqiyatli topshirildi',
            'attempt_id': attempt.id,
            'status': attempt.status,
            'listening_submitted': True,
            'auto_completed': auto_completed,
            'total_questions': total_questions,
            'answered_questions': len(answers_to_create),
            'time_spent': time_spent,
        }

        # Warning
        unanswered = total_questions - len(answers_to_create)
        if unanswered > 0:
            response_data['warning'] = f"{unanswered} ta savol bo'sh qoldi"

        return Response(response_data, status=status.HTTP_201_CREATED)


# ==================== READING VIEWSET ====================
@extend_schema(tags=['Reading Submit'])
class ReadingSubmissionViewSet(viewsets.ViewSet):
    """Reading javoblarini boshqarish"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Reading sectionni boshlash

        POST /api/reading/start/
        {
            "test_id": 1
        }

        Response:
        {
            "attempt_id": 123,
            "time_limit": 3600,  // 60 daqiqa
            "started_at": "2025-12-07T10:30:00Z"
        }
        """
        test_id = request.data.get('test_id')
        if not test_id:
            return Response(
                {'error': 'test_id majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test = get_object_or_404(Test, pk=test_id)

        # Attempt olish
        try:
            attempt = TestAttempt.objects.get(user=request.user, test=test)
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Avval test boshlang'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reading allaqachon submitted bo'lsa
        if attempt.reading_submitted:
            return Response(
                {'error': 'Reading allaqachon topshirilgan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reading start time
        if not attempt.reading_started_at:
            attempt.reading_started_at = timezone.now()
            attempt.save(update_fields=['reading_started_at'])

        return Response({
            'attempt_id': attempt.id,
            'time_limit': 3600,  # 60 minutes
            'started_at': attempt.reading_started_at,
        })

    @extend_schema(
        request=ReadingSubmitSerializer,
        responses={201: TestAttemptDetailSerializer}
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit(self, request):
        """Reading javoblarini yuborish (FAQAT BIR MARTA)"""
        serializer = ReadingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_id = serializer.validated_data['test_id']
        answers = serializer.validated_data['answers']
        time_spent = serializer.validated_data['time_spent']

        test = get_object_or_404(Test, pk=test_id)

        # Attempt olish
        try:
            attempt = TestAttempt.objects.get(user=request.user, test=test)
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Avval /reading/start/ ni chaqiring'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Allaqachon submitted bo'lsa, REJECT
        if attempt.reading_submitted:
            return Response(
                {'error': 'Reading allaqachon topshirilgan. Qayta yuborib bo\'lmaydi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attempt.status == 'completed':
            return Response(
                {'error': 'Test tugallangan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Questionlarni olish
        questions = ReadingQuestion.objects.filter(
            passage__test=test
        ).select_related('passage')

        total_questions = questions.count()
        question_map = {str(q.question_number): q for q in questions}

        # Javoblarni saqlash
        answers_to_create = []
        for q_number_str, user_answer in answers.items():
            question = question_map.get(q_number_str)
            if question:
                answers_to_create.append(
                    ReadingAnswer(
                        attempt=attempt,
                        question=question,
                        user_answer=user_answer.strip()
                    )
                )

        ReadingAnswer.objects.filter(attempt=attempt).delete()
        if answers_to_create:
            ReadingAnswer.objects.bulk_create(answers_to_create)

        # ✅ Reading ni submitted qilish
        attempt.reading_submitted = True
        attempt.reading_submitted_at = timezone.now()
        attempt.save(update_fields=['reading_submitted', 'reading_submitted_at'])

        # Auto complete check
        auto_completed = check_and_complete_attempt(attempt)

        response_data = {
            'message': 'Reading muvaffaqiyatli topshirildi',
            'attempt_id': attempt.id,
            'status': attempt.status,
            'reading_submitted': True,
            'auto_completed': auto_completed,
            'total_questions': total_questions,
            'answered_questions': len(answers_to_create),
            'time_spent': time_spent,
        }

        unanswered = total_questions - len(answers_to_create)
        if unanswered > 0:
            response_data['warning'] = f"{unanswered} ta savol bo'sh qoldi"

        return Response(response_data, status=status.HTTP_201_CREATED)


# ==================== WRITING VIEWSET ====================
@extend_schema(tags=['Writing Submit'])
class WritingSubmissionViewSet(viewsets.ViewSet):
    """Writing javoblarini boshqarish"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Writing sectionni boshlash

        POST /api/writing/start/
        {
            "test_id": 1
        }
        """
        test_id = request.data.get('test_id')
        if not test_id:
            return Response(
                {'error': 'test_id majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test = get_object_or_404(Test, pk=test_id)

        try:
            attempt = TestAttempt.objects.get(user=request.user, test=test)
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Avval test boshlang'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attempt.writing_submitted:
            return Response(
                {'error': 'Writing allaqachon topshirilgan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not attempt.writing_started_at:
            attempt.writing_started_at = timezone.now()
            attempt.save(update_fields=['writing_started_at'])

        return Response({
            'attempt_id': attempt.id,
            'time_limit': 3600,  # 60 minutes
            'started_at': attempt.writing_started_at,
        })

    @extend_schema(
        request=WritingSubmitSerializer,
        responses={201: TestAttemptDetailSerializer}
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit(self, request):
        """Writing javoblarini yuborish (FAQAT BIR MARTA)"""
        serializer = WritingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_id = serializer.validated_data['test_id']
        task1_text = serializer.validated_data.get('task1_text', '').strip()
        task2_text = serializer.validated_data.get('task2_text', '').strip()
        time_spent = serializer.validated_data['time_spent']

        test = get_object_or_404(Test, pk=test_id)

        try:
            attempt = TestAttempt.objects.get(user=request.user, test=test)
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Avval /writing/start/ ni chaqiring'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Allaqachon submitted bo'lsa, REJECT
        if attempt.writing_submitted:
            return Response(
                {'error': 'Writing allaqachon topshirilgan. Qayta yuborib bo\'lmaydi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attempt.status == 'completed':
            return Response(
                {'error': 'Test tugallangan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Tasklarni olish
        tasks = WritingTask.objects.filter(test=test).order_by('task_number')
        if tasks.count() < 2:
            return Response(
                {'error': 'Bu testda 2 ta writing task yo\'q'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Avvalgilarni o'chirish
        WritingSubmission.objects.filter(attempt=attempt).delete()

        # Yangi submissionlar
        task1_submission = None
        task2_submission = None

        if task1_text:
            task1_submission = WritingSubmission.objects.create(
                attempt=attempt,
                task=tasks[0],
                submission_text=task1_text,
                time_spent=time_spent
            )

        if task2_text:
            task2_submission = WritingSubmission.objects.create(
                attempt=attempt,
                task=tasks[1],
                submission_text=task2_text,
                time_spent=time_spent
            )

        # ✅ Writing ni submitted qilish
        attempt.writing_submitted = True
        attempt.writing_submitted_at = timezone.now()
        attempt.save(update_fields=['writing_submitted', 'writing_submitted_at'])

        # Auto complete
        auto_completed = check_and_complete_attempt(attempt)

        response_data = {
            'message': 'Writing muvaffaqiyatli topshirildi',
            'attempt_id': attempt.id,
            'status': attempt.status,
            'writing_submitted': True,
            'auto_completed': auto_completed,
            'task1_word_count': task1_submission.word_count if task1_submission else 0,
            'task2_word_count': task2_submission.word_count if task2_submission else 0,
            'time_spent': time_spent,
        }

        warnings = []
        if not task1_text:
            warnings.append("Task 1 bo'sh")
        if not task2_text:
            warnings.append("Task 2 bo'sh")
        if warnings:
            response_data['warning'] = ", ".join(warnings)

        return Response(response_data, status=status.HTTP_201_CREATED)













# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from django.shortcuts import get_object_or_404
# from django.db import transaction
# from django.utils import timezone
# from drf_spectacular.utils import extend_schema, OpenApiParameter
#
# from app.models import (
#     TestAttempt, ListeningAnswer, ReadingAnswer, WritingSubmission
# )
# from app.models import Test, ListeningQuestion, ReadingQuestion, WritingTask
# from app.serializers import (
#     ListeningSubmitSerializer,
#     ReadingSubmitSerializer,
#     WritingSubmitSerializer,
#     TestAttemptListSerializer,
#     TestAttemptDetailSerializer,
#     GradeAttemptSerializer
# )
#
#
# def check_and_complete_attempt(attempt):
#     """
#     Agar barcha sectionlar topshirilgan bo'lsa, avtomatik completed qilish
#
#     Returns:
#         bool: True agar completed qilingan bo'lsa
#     """
#     has_listening = attempt.listening_answers.exists()
#     has_reading = attempt.reading_answers.exists()
#     has_writing = attempt.writing_submissions.exists()
#
#     # Barcha 3 ta section topshirilgan bo'lsa
#     if has_listening and has_reading and has_writing:
#         if attempt.status != 'completed':
#             attempt.mark_completed()
#             return True
#
#     return False
#
#
# # ==================== LISTENING VIEWSET ====================
# @extend_schema(tags=['Listening Submit'])
# class ListeningSubmissionViewSet(viewsets.ViewSet):
#     """Listening javoblarini boshqarish"""
#     permission_classes = [IsAuthenticated]
#
#     @extend_schema(
#         request=ListeningSubmitSerializer,
#         responses={201: TestAttemptDetailSerializer}
#     )
#     @action(detail=False, methods=['post'])
#     @transaction.atomic
#     def submit(self, request):
#         """Barcha listening javoblarini bir vaqtda yuborish (40 ta savol)"""
#         serializer = ListeningSubmitSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         test_id = serializer.validated_data['test_id']
#         answers = serializer.validated_data['answers']
#         time_spent = serializer.validated_data['time_spent']
#
#         test = get_object_or_404(Test, pk=test_id)
#
#         # TestAttempt yaratish yoki olish
#         attempt, created = TestAttempt.objects.get_or_create(
#             user=request.user,
#             test=test,
#             defaults={'status': 'in_progress'}
#         )
#
#         # Completed bo'lsa javob qabul qilinmaydi
#         if attempt.status == 'completed':
#             return Response(
#                 {'error': 'Test allaqachon tugallangan. Javoblarni o\'zgartirib bo\'lmaydi'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Barcha listening questionlarni olish
#         questions = ListeningQuestion.objects.filter(
#             section__test=test
#         ).select_related('section')
#
#         total_questions = questions.count()
#         question_map = {str(q.question_number): q for q in questions}
#
#         # Javoblarni saqlash
#         answers_to_create = []
#
#         for q_number_str, user_answer in answers.items():
#             question = question_map.get(q_number_str)
#             if question:
#                 answers_to_create.append(
#                     ListeningAnswer(
#                         attempt=attempt,
#                         question=question,
#                         user_answer=user_answer.strip()
#                     )
#                 )
#
#         # Avvalgi javoblarni o'chirish va yangilarini saqlash
#         ListeningAnswer.objects.filter(attempt=attempt).delete()
#         if answers_to_create:
#             ListeningAnswer.objects.bulk_create(answers_to_create)
#
#         # Avtomatik completed check
#         auto_completed = check_and_complete_attempt(attempt)
#
#         # Response tayyorlash
#         response_data = {
#             'message': 'Listening javoblari muvaffaqiyatli saqlandi',
#             'attempt_id': attempt.id,
#             'status': attempt.status,
#             'auto_completed': auto_completed,
#             'total_questions': total_questions,
#             'answered_questions': len(answers_to_create),
#             'time_spent': time_spent,
#         }
#
#         # ✅ Soft warning - bo'sh savollar haqida
#         unanswered = total_questions - len(answers_to_create)
#         if unanswered > 0:
#             response_data['warning'] = f"{unanswered} ta savol bo'sh qoldi"
#
#         return Response(response_data, status=status.HTTP_201_CREATED)
#
#
# # ==================== READING VIEWSET ====================
# @extend_schema(tags=['Reading Submit'])
# class ReadingSubmissionViewSet(viewsets.ViewSet):
#     """Reading javoblarini boshqarish"""
#     permission_classes = [IsAuthenticated]
#
#     @extend_schema(
#         request=ReadingSubmitSerializer,
#         responses={201: TestAttemptDetailSerializer}
#     )
#     @action(detail=False, methods=['post'])
#     @transaction.atomic
#     def submit(self, request):
#         """Barcha reading javoblarini bir vaqtda yuborish (40 ta savol)"""
#         serializer = ReadingSubmitSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         test_id = serializer.validated_data['test_id']
#         answers = serializer.validated_data['answers']
#         time_spent = serializer.validated_data['time_spent']
#
#         test = get_object_or_404(Test, pk=test_id)
#
#         # TestAttempt yaratish yoki olish
#         attempt, created = TestAttempt.objects.get_or_create(
#             user=request.user,
#             test=test,
#             defaults={'status': 'in_progress'}
#         )
#
#         # Completed bo'lsa javob qabul qilinmaydi
#         if attempt.status == 'completed':
#             return Response(
#                 {'error': 'Test allaqachon tugallangan. Javoblarni o\'zgartirib bo\'lmaydi'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Barcha reading questionlarni olish
#         questions = ReadingQuestion.objects.filter(
#             passage__test=test
#         ).select_related('passage')
#
#         total_questions = questions.count()
#         question_map = {str(q.question_number): q for q in questions}
#
#         # Javoblarni saqlash
#         answers_to_create = []
#
#         for q_number_str, user_answer in answers.items():
#             question = question_map.get(q_number_str)
#             if question:
#                 answers_to_create.append(
#                     ReadingAnswer(
#                         attempt=attempt,
#                         question=question,
#                         user_answer=user_answer.strip()
#                     )
#                 )
#
#         # Avvalgi javoblarni o'chirish va yangilarini saqlash
#         ReadingAnswer.objects.filter(attempt=attempt).delete()
#         if answers_to_create:
#             ReadingAnswer.objects.bulk_create(answers_to_create)
#
#         # Avtomatik completed check
#         auto_completed = check_and_complete_attempt(attempt)
#
#         # Response tayyorlash
#         response_data = {
#             'message': 'Reading javoblari muvaffaqiyatli saqlandi',
#             'attempt_id': attempt.id,
#             'status': attempt.status,
#             'auto_completed': auto_completed,
#             'total_questions': total_questions,
#             'answered_questions': len(answers_to_create),
#             'time_spent': time_spent,
#         }
#
#         # ✅ Soft warning - bo'sh savollar haqida
#         unanswered = total_questions - len(answers_to_create)
#         if unanswered > 0:
#             response_data['warning'] = f"{unanswered} ta savol bo'sh qoldi"
#
#         return Response(response_data, status=status.HTTP_201_CREATED)
#
#
#
# # ==================== WRITING VIEWSET ====================
# @extend_schema(tags=['Writing Submit'])
# class WritingSubmissionViewSet(viewsets.ViewSet):
#     """Writing javoblarini boshqarish"""
#     permission_classes = [IsAuthenticated]
#
#     @extend_schema(
#         request=WritingSubmitSerializer,
#         responses={201: TestAttemptDetailSerializer}
#     )
#     @action(detail=False, methods=['post'])
#     @transaction.atomic
#     def submit(self, request):
#         """
#         Ikkala writing taskni bir vaqtda yuborish
#
#         POST /api/writing/submit/
#         {
#             "test_id": 1,
#             "task1_text": "Task 1 essay matni...",
#             "task2_text": "Task 2 essay matni...",
#             "time_spent": 3500  // ✅ Umumiy vaqt
#         }
#         """
#         serializer = WritingSubmitSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         test_id = serializer.validated_data['test_id']
#         task1_text = serializer.validated_data.get('task1_text', '').strip()
#         task2_text = serializer.validated_data.get('task2_text', '').strip()
#         time_spent = serializer.validated_data['time_spent']  # ✅ Umumiy
#
#         test = get_object_or_404(Test, pk=test_id)
#
#         # TestAttempt yaratish yoki olish
#         attempt, created = TestAttempt.objects.get_or_create(
#             user=request.user,
#             test=test,
#             defaults={'status': 'in_progress'}
#         )
#
#         # Completed bo'lsa javob qabul qilinmaydi
#         if attempt.status == 'completed':
#             return Response(
#                 {'error': 'Test allaqachon tugallangan. Javoblarni o\'zgartirib bo\'lmaydi'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Writing tasklarni olish
#         tasks = WritingTask.objects.filter(test=test).order_by('task_number')
#
#         if tasks.count() < 2:
#             return Response(
#                 {'error': 'Bu testda 2 ta writing task yo\'q'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         task1 = tasks[0]
#         task2 = tasks[1]
#
#         # Avvalgi submissionlarni o'chirish
#         WritingSubmission.objects.filter(attempt=attempt).delete()
#
#         # Task 1 ni saqlash
#         task1_submission = None
#         if task1_text:
#             task1_submission = WritingSubmission.objects.create(
#                 attempt=attempt,
#                 task=task1,
#                 submission_text=task1_text,
#                 time_spent=0  # ✅ Individual time yo'q
#             )
#
#         # Task 2 ni saqlash
#         task2_submission = None
#         if task2_text:
#             task2_submission = WritingSubmission.objects.create(
#                 attempt=attempt,
#                 task=task2,
#                 submission_text=task2_text,
#                 time_spent=0  # ✅ Individual time yo'q
#             )
#
#         # Avtomatik completed check
#         auto_completed = check_and_complete_attempt(attempt)
#
#         # Response tayyorlash
#         response_data = {
#             'message': 'Writing javoblari muvaffaqiyatli saqlandi',
#             'attempt_id': attempt.id,
#             'status': attempt.status,
#             'auto_completed': auto_completed,
#             'task1_word_count': task1_submission.word_count if task1_submission else 0,
#             'task2_word_count': task2_submission.word_count if task2_submission else 0,
#             'time_spent': time_spent,  # ✅ Umumiy vaqt
#         }
#
#         # ✅ Warning - bo'sh tasklar haqida
#         warnings = []
#         if not task1_text:
#             warnings.append("Task 1 bo'sh qoldirildi")
#         if not task2_text:
#             warnings.append("Task 2 bo'sh qoldirildi")
#
#         if warnings:
#             response_data['warning'] = ", ".join(warnings)
#
#         return Response(response_data, status=status.HTTP_201_CREATED)

# ==================== TEST ATTEMPT VIEWSET ====================


@extend_schema(tags=['Test Attempts'])
class TestAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Test attemptlarini ko'rish va boshqarish"""
    permission_classes = [IsAuthenticated]
    serializer_class = TestAttemptDetailSerializer

    def get_queryset(self):
        user = self.request.user

        # Student faqat o'ziniki
        if user.role == 'student':
            return TestAttempt.objects.filter(
                user=user
            ).select_related('test', 'graded_by').prefetch_related(
                'listening_answers__question__section',
                'reading_answers__question__passage',
                'writing_submissions__task'
            )

        # Teacher/Admin barchasi
        return TestAttempt.objects.all().select_related(
            'test', 'user', 'graded_by'
        ).prefetch_related(
            'listening_answers__question__section',
            'reading_answers__question__passage',
            'writing_submissions__task'
        )

    @extend_schema(
        parameters=[
            OpenApiParameter('status', str, description='Filter by status'),
            OpenApiParameter('graded', bool, description='Filter by graded status'),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Attemptlar ro'yxati

        Query params:
        - status: in_progress, completed
        - graded: true, false
        """
        queryset = self.get_queryset()

        # Filters
        status_filter = request.query_params.get('status')
        graded_filter = request.query_params.get('graded')

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if graded_filter is not None:
            if graded_filter.lower() == 'true':
                queryset = queryset.filter(graded_at__isnull=False)
            else:
                queryset = queryset.filter(graded_at__isnull=True)

        serializer = TestAttemptListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=GradeAttemptSerializer,
        responses={200: TestAttemptDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def grade(self, request, pk=None):
        """
        Teacher attempt ni baholash

        POST /api/attempts/{id}/grade/
        {
            "listening_band": 7.5,
            "reading_band": 7.0,
            "writing_band": 6.5,
            "teacher_comment": "Good performance overall..."
        }
        """
        # Faqat teacher/admin
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Faqat teacher baholashi mumkin'},
                status=status.HTTP_403_FORBIDDEN
            )

        attempt = self.get_object()

        serializer = GradeAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Band scorelarni yangilash
        if serializer.validated_data.get('listening_band') is not None:
            attempt.listening_band = serializer.validated_data['listening_band']

        if serializer.validated_data.get('reading_band') is not None:
            attempt.reading_band = serializer.validated_data['reading_band']

        if serializer.validated_data.get('writing_band') is not None:
            attempt.writing_band = serializer.validated_data['writing_band']

        if serializer.validated_data.get('teacher_comment'):
            attempt.teacher_comment = serializer.validated_data['teacher_comment']

        # Overall band ni hisoblash
        attempt.calculate_overall_band()

        # Grading info
        attempt.graded_by = request.user
        attempt.graded_at = timezone.now()
        attempt.save()

        return Response({
            'message': 'Baho muvaffaqiyatli qo\'yildi',
            'attempt': TestAttemptDetailSerializer(attempt).data
        })

    @extend_schema(
        responses={200: TestAttemptListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def ungraded(self, request):
        """
        Baholanmagan attemptlar (Teacher uchun)

        GET /api/attempts/ungraded/
        """
        if request.user.role not in ['teacher', 'admin']:
            return Response(
                {'error': 'Faqat teacher ko\'rishi mumkin'},
                status=status.HTTP_403_FORBIDDEN
            )

        attempts = TestAttempt.objects.filter(
            status='completed',
            graded_at__isnull=True
        ).select_related('test', 'user')

        serializer = TestAttemptListSerializer(attempts, many=True)
        return Response(serializer.data)








