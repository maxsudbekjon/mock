# core/serializers/listening_serializer.py

from rest_framework import serializers
from app.models import (
    ListeningSection,
    ListeningQuestion,
    ListeningAnswer,
    TestAttempt
)


class ListeningQuestionSerializer(serializers.ModelSerializer):
    """
    Listening question - Student uchun
    To'g'ri javob ko'rinmaydi
    """

    class Meta:
        model = ListeningQuestion
        fields = [
            'id',
            'question_number',
            'question_text',
            'question_type',  # 'written' yoki 'options'
            'options',  # Agar 'options' type bo'lsa
        ]


class ListeningQuestionAdminSerializer(serializers.ModelSerializer):
    """
    Admin/Teacher uchun - javob bilan
    """

    class Meta:
        model = ListeningQuestion
        fields = [
            'id',
            'question_number',
            'question_text',
            'question_type',
            'options',
            'correct_answer',  # Teacher ko'radi
            'points',
            'explanation'
        ]


class ListeningSectionSerializer(serializers.ModelSerializer):
    """
    Student test boshlashida oladi
    """
    questions = ListeningQuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = ListeningSection
        fields = [
            'id',
            'section_number',
            'audio_file',
            'audio_duration',
            'instructions',
            'questions',
            'question_count'
        ]

    def get_question_count(self, obj) -> int:
        return obj.questions.count()


class ListeningAnswerSubmitSerializer(serializers.Serializer):
    """
    Student javob yuborish
    """
    question_id = serializers.IntegerField(required=True)
    user_answer = serializers.CharField(required=True, allow_blank=True)

    def validate_question_id(self, value):
        if not ListeningQuestion.objects.filter(id=value).exists():
            raise serializers.ValidationError("Question not found")
        return value


class ListeningAnswerSerializer(serializers.ModelSerializer):
    """
    Student answer
    """
    question_number = serializers.IntegerField(source='question.question_number', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = ListeningAnswer
        fields = [
            'id',
            'question',
            'question_number',
            'question_text',
            'user_answer',
            'answered_at'
        ]
        read_only_fields = ['id', 'answered_at']


class ListeningAnswerForTeacherSerializer(serializers.ModelSerializer):
    """
    Teacher uchun - checking uchun
    Student ma'lumotlari bilan
    """
    question_number = serializers.IntegerField(source='question.question_number', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    options = serializers.JSONField(source='question.options', read_only=True)
    correct_answer = serializers.CharField(source='question.correct_answer', read_only=True)
    points = serializers.IntegerField(source='question.points', read_only=True)
    student_name = serializers.CharField(source='attempt.user.get_full_name', read_only=True)

    class Meta:
        model = ListeningAnswer
        fields = [
            'id',
            'student_name',
            'question_number',
            'question_text',
            'question_type',
            'options',
            'user_answer',
            'correct_answer',
            'points',
            'is_correct',
            'answered_at'
        ]
        read_only_fields = ['id', 'answered_at']


class ListeningGradeSerializer(serializers.Serializer):
    """
    Teacher javobni baholash uchun
    """
    answer_id = serializers.IntegerField(required=True)
    is_correct = serializers.BooleanField(required=True)

    def validate_answer_id(self, value):
        if not ListeningAnswer.objects.filter(id=value).exists():
            raise serializers.ValidationError("Answer not found")
        return value


class ListeningBulkGradeSerializer(serializers.Serializer):
    """
    Teacher bir nechta javobni bir vaqtda baholash
    """
    grades = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    # grades format: [
    #   {"answer_id": 1, "is_correct": true, "teacher_comment": "Good"},
    #   {"answer_id": 2, "is_correct": false, "teacher_comment": "Wrong"}
    # ]


class ListeningStudentResultSerializer(serializers.ModelSerializer):
    """
    Student o'z natijasini ko'rish (teacher baholagandan keyin)
    """
    question_number = serializers.IntegerField(source='question.question_number', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    options = serializers.JSONField(source='question.options', read_only=True)
    correct_answer = serializers.CharField(source='question.correct_answer', read_only=True)
    points = serializers.IntegerField(source='question.points', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)

    class Meta:
        model = ListeningAnswer
        fields = [
            'question_number',
            'question_text',
            'question_type',
            'options',
            'user_answer',
            'correct_answer',
            'is_correct',
            'points',
            'explanation'
        ]


class ListeningResultSummarySerializer(serializers.Serializer):
    """
    Listening natija summary
    """
    attempt_id = serializers.IntegerField()
    student_name = serializers.CharField()
    total_questions = serializers.IntegerField()
    graded_questions = serializers.IntegerField()
    ungraded_questions = serializers.IntegerField()
    correct_answers = serializers.IntegerField()
    incorrect_answers = serializers.IntegerField()
    total_points = serializers.IntegerField()
    earned_points = serializers.IntegerField()
    percentage = serializers.FloatField()
    is_fully_graded = serializers.BooleanField()