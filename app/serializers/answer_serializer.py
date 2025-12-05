
from rest_framework import serializers
from django.utils import timezone
from app.models import TestAttempt



class TestAttemptDetailSerializer(serializers.ModelSerializer):
    """Attempt bilan birga vaqt ma'lumotlari"""

    listening_remaining_time = serializers.SerializerMethodField()
    reading_remaining_time = serializers.SerializerMethodField()
    writing_remaining_time = serializers.SerializerMethodField()

    listening_duration = serializers.IntegerField(source='test.listening_duration', read_only=True)
    reading_duration = serializers.IntegerField(source='test.reading_duration', read_only=True)
    writing_duration = serializers.IntegerField(source='test.writing_duration', read_only=True)

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test', 'status', 'started_at',
            # Vaqt ma'lumotlari
            'listening_started_at', 'listening_completed_at', 'listening_remaining_time', 'listening_duration',
            'reading_started_at', 'reading_completed_at', 'reading_remaining_time', 'reading_duration',
            'writing_started_at', 'writing_completed_at', 'writing_remaining_time', 'writing_duration',
            # Ballar
            'listening_score', 'reading_score', 'overall_band_score'
        ]

    def get_listening_remaining_time(self, obj):
        """Listening qolgan vaqt (soniya)"""
        return obj.get_remaining_time('listening')

    def get_reading_remaining_time(self, obj):
        return obj.get_remaining_time('reading')

    def get_writing_remaining_time(self, obj):
        return obj.get_remaining_time('writing')


# serializers.py
from rest_framework import serializers
from app.models import TestAttempt, ListeningAnswer, ReadingAnswer, WritingSubmission


class SubmitListeningAnswerSerializer(serializers.Serializer):
    """Bitta listening javobni yuborish"""
    question_id = serializers.IntegerField()
    user_answer = serializers.CharField(max_length=500)
    time_spent = serializers.IntegerField(default=0)


class BulkListeningAnswersSerializer(serializers.Serializer):
    """Ko'p listening javoblarni yuborish"""
    answers = SubmitListeningAnswerSerializer(many=True)


class ListeningAnswerSerializer(serializers.ModelSerializer):
    question_number = serializers.IntegerField(source='question.question_number', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    correct_answer = serializers.CharField(source='question.correct_answer', read_only=True)

    class Meta:
        model = ListeningAnswer
        fields = [
            'id', 'question', 'question_number', 'question_text',
            'user_answer', 'is_correct', 'correct_answer',
            'time_spent', 'answered_at'
        ]
        read_only_fields = ['is_correct', 'answered_at']


class TestAttemptSerializer(serializers.ModelSerializer):
    listening_answers = ListeningAnswerSerializer(many=True, read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test', 'test_title', 'user_name',
            'started_at', 'completed_at', 'status', 'time_spent',
            'listening_score', 'reading_score', 'writing_score', 'overall_band_score',
            'listening_answers'
        ]
        read_only_fields = [
            'user', 'started_at', 'listening_score',
            'reading_score', 'writing_score', 'overall_band_score'
        ]


class TestAttemptListSerializer(serializers.ModelSerializer):
    """List uchun yengil serializer (javoblarsiz)"""
    test_title = serializers.CharField(source='test.title', read_only=True)

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test', 'test_title', 'started_at', 'completed_at',
            'status', 'listening_score', 'overall_band_score'
        ]