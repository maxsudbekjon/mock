from rest_framework import serializers
from app.models import TestAttempt, ListeningAnswer, ReadingAnswer, WritingSubmission
from app.models import Test, ListeningQuestion, ReadingQuestion, WritingTask


# ==================== LISTENING SERIALIZERS ====================
class ListeningSubmitSerializer(serializers.Serializer):
    """Listening barcha javoblarini submit qilish"""

    test_id = serializers.IntegerField()
    answers = serializers.DictField(
        child=serializers.CharField(max_length=500, allow_blank=True),
        help_text="Question number: answer. Example: {'1': 'A', '2': 'library'}"
    )
    time_spent = serializers.IntegerField(min_value=0, help_text="Sekundlarda")

    def validate_test_id(self, value):
        if not Test.objects.filter(id=value).exists():
            raise serializers.ValidationError("Test topilmadi")
        return value

    def validate_answers(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Answers must be a dictionary")

        if len(value) == 0:
            raise serializers.ValidationError("Kamida 1 ta javob kerak")

        # ✅ Maksimal 40 ta javob
        if len(value) > 40:
            raise serializers.ValidationError("Juda ko'p javob (maksimal 40)")

        # Question numberlar valid ekanini tekshirish
        for q_num in value.keys():
            try:
                num = int(q_num)
                if num < 1 or num > 40:
                    raise serializers.ValidationError(f"Question number 1-40 oralig'ida bo'lishi kerak: {q_num}")
            except ValueError:
                raise serializers.ValidationError(f"Invalid question number: {q_num}")

        return value

class ListeningAnswerDetailSerializer(serializers.ModelSerializer):
    """Listening javob detallari"""
    question_number = serializers.IntegerField(source='question.question_number')
    question_text = serializers.CharField(source='question.question_text')
    section_number = serializers.IntegerField(source='question.section.section_number')

    class Meta:
        model = ListeningAnswer
        fields = ['question_number', 'section_number', 'question_text', 'user_answer', 'answered_at']


# ==================== READING SERIALIZERS ====================
class ReadingSubmitSerializer(serializers.Serializer):
    """Reading barcha javoblarini submit qilish"""

    test_id = serializers.IntegerField()
    answers = serializers.DictField(
        child=serializers.CharField(max_length=500, allow_blank=True),
        help_text="Question number: answer. Example: {'1': 'TRUE', '2': 'FALSE'}"
    )
    time_spent = serializers.IntegerField(min_value=0, help_text="Sekundlarda")

    def validate_test_id(self, value):
        if not Test.objects.filter(id=value).exists():
            raise serializers.ValidationError("Test topilmadi")
        return value

    def validate_answers(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Answers must be a dictionary")

        if len(value) == 0:
            raise serializers.ValidationError("Kamida 1 ta javob kerak")

        # ✅ Maksimal 40 ta javob
        if len(value) > 40:
            raise serializers.ValidationError("Juda ko'p javob (maksimal 40)")

        for q_num in value.keys():
            try:
                num = int(q_num)
                if num < 1 or num > 40:
                    raise serializers.ValidationError(f"Question number 1-40 oralig'ida bo'lishi kerak: {q_num}")
            except ValueError:
                raise serializers.ValidationError(f"Invalid question number: {q_num}")

        return value

    def validate_time_spent(self, value):
        """Reading 60 daqiqadan oshmasligi kerak"""
        if value > 3600:  # 60 minutes
            raise serializers.ValidationError("Reading time cannot exceed 60 minutes")
        return value

class ReadingAnswerDetailSerializer(serializers.ModelSerializer):
    """Reading javob detallari"""
    question_number = serializers.IntegerField(source='question.question_number')
    question_text = serializers.CharField(source='question.question_text')
    passage_number = serializers.IntegerField(source='question.passage.passage_number')

    class Meta:
        model = ReadingAnswer
        fields = ['question_number', 'passage_number', 'question_text', 'user_answer', 'answered_at']


# ==================== WRITING SERIALIZERS ====================
class WritingSubmitSerializer(serializers.Serializer):
    """Writing ikkala taskni submit qilish"""

    test_id = serializers.IntegerField()

    # Task texts
    task1_text = serializers.CharField(allow_blank=True, required=False)
    task2_text = serializers.CharField(allow_blank=True, required=False)

    # ✅ UMUMIY time_spent
    time_spent = serializers.IntegerField(
        min_value=0,
        help_text="Jami vaqt sekundlarda (task1 + task2)"
    )

    def validate_time_spent(self, value):
        """Writing 60 daqiqadan oshmasligi kerak"""
        if value > 3600:  # 60 minutes
            raise serializers.ValidationError("Writing time cannot exceed 60 minutes")
        return value

    def validate(self, data):
        """Kamida bitta task to'ldirilgan bo'lishi kerak"""
        task1 = data.get('task1_text', '').strip()
        task2 = data.get('task2_text', '').strip()

        if not task1 and not task2:
            raise serializers.ValidationError("Kamida bitta task to'ldirilishi kerak")

        return data

class WritingSubmissionDetailSerializer(serializers.ModelSerializer):
    """Writing submission detallari"""
    task_number = serializers.IntegerField(source='task.task_number')
    task_type = serializers.CharField(source='task.task_type')

    class Meta:
        model = WritingSubmission
        fields = [
            'task_number', 'task_type', 'submission_text',
            'word_count', 'time_spent', 'submitted_at'
        ]


# ==================== ATTEMPT SERIALIZERS ====================
class TestAttemptListSerializer(serializers.ModelSerializer):
    """Attempt ro'yxati uchun"""
    test_title = serializers.CharField(source='test.title')
    student_name = serializers.CharField(source='user.username')

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test_title', 'student_name', 'status',
            'started_at', 'completed_at', 'listening_band',
            'reading_band', 'writing_band', 'overall_band',
            'graded_at', 'is_graded'
        ]

    is_graded = serializers.SerializerMethodField()

    def get_is_graded(self, obj):
        return obj.is_graded()


class TestAttemptDetailSerializer(serializers.ModelSerializer):
    """Attempt detallari"""
    test_title = serializers.CharField(source='test.title')
    student_name = serializers.CharField(source='user.username')
    graded_by_name = serializers.CharField(source='graded_by.username', allow_null=True)

    listening_answers = ListeningAnswerDetailSerializer(many=True, read_only=True)
    reading_answers = ReadingAnswerDetailSerializer(many=True, read_only=True)
    writing_submissions = WritingSubmissionDetailSerializer(many=True, read_only=True)

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test_title', 'student_name', 'status',
            'started_at', 'completed_at',
            'listening_band', 'reading_band', 'writing_band', 'overall_band',
            'teacher_comment', 'graded_by_name', 'graded_at',
            'listening_answers', 'reading_answers', 'writing_submissions'
        ]


class GradeAttemptSerializer(serializers.Serializer):
    """Teacher baholash uchun"""

    listening_band = serializers.DecimalField(
        max_digits=2, decimal_places=1,
        min_value=0, max_value=9,
        required=False, allow_null=True
    )
    reading_band = serializers.DecimalField(
        max_digits=2, decimal_places=1,
        min_value=0, max_value=9,
        required=False, allow_null=True
    )
    writing_band = serializers.DecimalField(
        max_digits=2, decimal_places=1,
        min_value=0, max_value=9,
        required=False, allow_null=True
    )
    teacher_comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Kamida bitta band score bo'lishi kerak"""
        if not any([
            data.get('listening_band'),
            data.get('reading_band'),
            data.get('writing_band')
        ]):
            raise serializers.ValidationError("Kamida bitta band score kiriting")
        return data