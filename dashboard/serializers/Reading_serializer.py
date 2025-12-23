
from rest_framework import serializers
from app.models import ReadingPassage, ReadingQuestion, Test


class TestBasicSerializer(serializers.ModelSerializer):
    """Basic Test information for nested use"""

    class Meta:
        model = Test
        fields = ['id', 'title']
        read_only_fields = fields



class ReadingQuestionListSerializer(serializers.ModelSerializer):
    """
    O'quvchilar uchun - correct_answer ni yashirish
    """
    # options = serializers.ReadOnlyField()
    # matching_items = serializers.ReadOnlyField()
    # word_limit = serializers.ReadOnlyField()

    class Meta:
        model = ReadingQuestion
        fields = [
            'id',
            'question_number',
            'question_text',
            'question_type',
            'question_data'
            # 'points',
            # Helper fields
            # 'options',
            # 'matching_items',
            # 'word_limit',
        ]


class ReadingQuestionSerializer(serializers.ModelSerializer):
    """
    Reading Question Serializer - O'qituvchilar uchun (to'liq)
    """

    # Helper fields - @property methodlardan avtomatik
    # options = serializers.ReadOnlyField()
    # matching_items = serializers.ReadOnlyField()
    # word_limit = serializers.ReadOnlyField()

    class Meta:
        model = ReadingQuestion
        fields = [
            'id',
            'passage',
            'question_number',
            'question_text',
            'question_type',
            'question_data',
            'correct_answer',
            # 'points',
            # Helper fields (read-only)
            # 'options',
            # 'matching_items',
            # 'word_limit',
        ]
        read_only_fields = ['id', 'question_number']

    def validate(self, data):
        """Validation - yangi model uchun"""
        question_type = data.get('question_type')
        question_data = data.get('question_data', {})

        if question_type == 'multiple_choice':
            if not question_data or 'options' not in question_data:
                raise serializers.ValidationError({
                    'question_data': 'Multiple choice uchun "options" kerak'
                })
            if not isinstance(question_data['options'], list) or len(question_data['options']) < 2:
                raise serializers.ValidationError({
                    'question_data': 'Kamida 2 ta variant bo\'lishi kerak'
                })

        elif question_type == 'matching':
            if not question_data or 'items' not in question_data:
                raise serializers.ValidationError({
                    'question_data': 'Matching uchun "items" kerak'
                })
            if not isinstance(question_data['items'], list):
                raise serializers.ValidationError({
                    'question_data': '"items" list bo\'lishi kerak'
                })

        return data


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
            'passage_text',
            'word_count',
            'questions_count'
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()



class ReadingPassageWithQuestionsSerializer(serializers.ModelSerializer):
    """Passage va uning savollari"""
    questions = serializers.SerializerMethodField()

    class Meta:
        model = ReadingPassage
        fields = [
            'id',
            'passage_number',
            'title',
            'passage_text',
            'word_count',
            'questions'
        ]

    def get_questions(self, obj):
        """Foydalanuvchi roliga qarab javob bilan yoki javobsiz qaytarish"""
        questions = obj.questions.all().order_by('question_number')
        request = self.context.get('request')

        if request and hasattr(request, 'user'):
            if request.user.role in ['teacher', 'admin']:
                return ReadingQuestionSerializer(questions, many=True).data

        return ReadingQuestionListSerializer(questions, many=True).data


class TestReadingOverviewSerializer(serializers.ModelSerializer):
    """Test va barcha passagelar + savollar"""
    reading_passages = ReadingPassageWithQuestionsSerializer(many=True, read_only=True)
    total_passages = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id',
            'title',
            'total_passages',
            'total_questions',
            'reading_passages'
        ]

    def get_total_passages(self, obj):
        return obj.reading_passages.count()

    def get_total_questions(self, obj):
        return ReadingQuestion.objects.filter(passage__test=obj).count()




class ReadingPassagesListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing passages"""
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = ReadingPassage
        fields = [
            'id',
            'passage_number',
            'title',
            'passage_text',
            'word_count',
            'questions_count'
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()





class ReadingPassageTestSerializer(serializers.ModelSerializer):
    """
    Test ma'lumoti va undagi barcha passagelar
    """
    reading_passages = ReadingPassagesListSerializer(many=True, read_only=True)
    passages_count = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id',
            'title',
            'description',  # agar Test modelida bo'lsa
            'passages_count',
            'total_questions',
            'reading_passages',
        ]

    def get_passages_count(self, obj):
        """Nechta passage bor"""
        return obj.reading_passages.count()

    def get_total_questions(self, obj):
        """Jami nechta savol bor (barcha passagelar bo'yicha)"""
        return sum(passage.questions.count() for passage in obj.reading_passages.all())







