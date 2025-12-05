# serializers.py

from rest_framework import serializers
from app.models import ReadingPassage, ReadingQuestion, Test


class TestBasicSerializer(serializers.ModelSerializer):
    """Basic Test information for nested use"""

    class Meta:
        model = Test
        fields = ['id', 'title']
        read_only_fields = fields


class ReadingQuestionSerializer(serializers.ModelSerializer):
    """Reading Question Serializer - for teachers"""

    class Meta:
        model = ReadingQuestion
        fields = [
            'id',
            'passage',
            'question_number',
            'question_text',
            'question_type',
            'options',
            'correct_answer',
            # 'points',
            # 'explanation'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """
        Modeldagi clean() metodiga o'xshash validatsiya.
        Agar type='options' bo'lsa, options maydoni bo'sh bo'lmasligi kerak.
        """
        question_type = data.get('question_type')
        options = data.get('options')

        if question_type == 'options' and not options:
            raise serializers.ValidationError(
                {"options": "Multiple Choice savollari uchun variantlar kiritilishi shart."}
            )
        return data

    def validate(self, attrs):
        """Cross-field validation"""
        question_type = attrs.get('question_type')
        options = attrs.get('options')

        if question_type == 'options' and not options:
            raise serializers.ValidationError({
                'options': 'Options are required for multiple choice questions'
            })

        return attrs


class ReadingQuestionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing questions (for students)"""

    class Meta:
        model = ReadingQuestion
        fields = [
            'id',
            'question_number',
            'question_text',
            'question_type',
            'options',
            # 'points'
        ]


class ReadingPassageSerializer(serializers.ModelSerializer):
    """Reading Passage Serializer - Full detail with questions"""
    questions = ReadingQuestionSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    test_info = TestBasicSerializer(source='test', read_only=True)

    class Meta:
        model = ReadingPassage
        fields = [
            'id',
            'test',
            'test_info',
            'passage_number',
            'title',
            'passage_text',
            'word_count',
            # 'source',
            'created_at',
            'questions',
            'questions_count'
        ]
        read_only_fields = ['id', 'word_count', 'created_at', 'test_info']

    def get_questions_count(self, obj):
        return obj.questions.count()


class ReadingPassageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating passage (WITHOUT questions)"""

    class Meta:
        model = ReadingPassage
        fields = [
            'id',
            'test',
            'passage_number',
            'title',
            'passage_text',
            'word_count',
            # 'source'
        ]
        read_only_fields = ['id', 'word_count']

    def validate_passage_number(self, value):
        """Validate passage number is between 1 and 3"""
        if value < 1 or value > 3:
            raise serializers.ValidationError("Passage number must be between 1 and 3")
        return value

    def validate(self, attrs):
        """Validate unique passage_number per test"""
        test = attrs.get('test')
        passage_number = attrs.get('passage_number')

        # Check if updating existing instance
        if self.instance:
            exists = ReadingPassage.objects.filter(
                test=test,
                passage_number=passage_number
            ).exclude(pk=self.instance.pk).exists()
        else:
            exists = ReadingPassage.objects.filter(
                test=test,
                passage_number=passage_number
            ).exists()

        if exists:
            raise serializers.ValidationError({
                'passage_number': f'Passage {passage_number} already exists for this test'
            })

        return attrs


class ReadingPassageListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing passages"""
    questions_count = serializers.SerializerMethodField()
    test_info = TestBasicSerializer(source='test', read_only=True)

    class Meta:
        model = ReadingPassage
        fields = [
            'id',
            'test_info',
            'passage_number',
            'title',
            'word_count',
            'questions_count'
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()


class TestReadingOverviewSerializer(serializers.ModelSerializer):
    """Serializer to show reading passages for a test"""
    reading_passages = ReadingPassageListSerializer(many=True, read_only=True)
    total_passages = serializers.SerializerMethodField()
    total_reading_questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id',
            'title',
            'total_passages',
            'total_reading_questions',
            'reading_passages'
        ]

    def get_total_passages(self, obj):
        return obj.reading_passages.count()

    def get_total_reading_questions(self, obj):
        total = 0
        for passage in obj.reading_passages.all():
            total += passage.questions.count()
        return total