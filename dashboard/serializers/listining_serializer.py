from rest_framework import serializers
from app.models import Test, ListeningSection, ListeningQuestion


class ListeningQuestionSerializer(serializers.ModelSerializer):
    """
    Listening Question Serializer - optimal model uchun
    O'qituvchilar/Admin uchun to'liq ma'lumot
    String va JSON formatlarni avtomatik qabul qiladi
    """

    class Meta:
        model = ListeningQuestion
        fields = [
            'id',
            'section',
            'question_number',
            'question_text',
            'question_type',
            'question_data',
            'question_image',
            # 'correct_answer',
        ]
        extra_kwargs = {
            'section': {'required': True},
            'question_number': {'required': True},
            'question_type': {'required': True},
            # 'correct_answer': {'write_only': True},  # Foydalanuvchiga ko'rsatmaslik
        }

    def validate(self, data):
        """Validation - model.clean() ga o'xshash"""
        question_type = data.get('question_type')
        question_data = data.get('question_data', {})
        question_image = data.get('question_image')

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
            if not question_data or 'left' not in question_data or 'right' not in question_data:
                raise serializers.ValidationError({
                    'question_data': 'Matching uchun "left" va "right" kerak'
                })
            if not isinstance(question_data['left'], list) or not isinstance(question_data['right'], list):
                raise serializers.ValidationError({
                    'question_data': '"left" va "right" list bo\'lishi kerak'
                })

        elif question_type == 'table':
            # Table uchun question_data YOKI question_image bo'lishi kerak
            has_data = question_data and 'headers' in question_data and 'rows' in question_data
            has_image = bool(question_image)

            if not has_data and not has_image:
                raise serializers.ValidationError(
                    'Table uchun question_data (headers, rows) yoki question_image kerak'
                )

        return data

    def validate_question_number(self, value):
        """question_number musbat son bo'lishi kerak"""
        if value <= 0:
            raise serializers.ValidationError('Question number musbat son bo\'lishi kerak')
        return value

# class ListeningQuestionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ListeningQuestion
#         fields = [
#             'id', 'section', 'question_number', 'question_text',
#             'question_type', 'options', 'correct_answer', 'points'
#         ]
#         extra_kwargs = {
#             'section': {'required': True}
#         }
#
#     def validate(self, data):
#         """
#         Modeldagi clean() metodiga o'xshash validatsiya.
#         Agar type='options' bo'lsa, options maydoni bo'sh bo'lmasligi kerak.
#         """
#         question_type = data.get('question_type')
#         options = data.get('options')
#
#         if question_type == 'options' and not options:
#             raise serializers.ValidationError(
#                 {"options": "Multiple Choice savollari uchun variantlar kiritilishi shart."}
#             )
#         return data


class ListeningSectionSerializer(serializers.ModelSerializer):
    # Sectionni o'qiganda uning ichidagi savollar sonini ham ko'rsatib ketish foydali
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = ListeningSection
        fields = [
            'id', 'test', 'section_number', 'audio_file',
            'audio_duration', 'instructions', 'created_at', 'questions_count'
        ]
        read_only_fields = ['created_at', 'questions_count']