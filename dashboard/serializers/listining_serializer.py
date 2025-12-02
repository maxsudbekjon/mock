from rest_framework import serializers
from app.models import Test, ListeningSection, ListeningQuestion





class ListeningQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListeningQuestion
        fields = [
            'id', 'section', 'question_number', 'question_text',
            'question_type', 'options', 'correct_answer', 'points'
        ]
        extra_kwargs = {
            'section': {'required': True}
        }

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