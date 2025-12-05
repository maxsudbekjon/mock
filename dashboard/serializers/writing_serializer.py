from rest_framework import serializers
from app.models import WritingTask, Test


class WritingTaskSerializer(serializers.ModelSerializer):
    """
    Teacher/Admin uchun - to'liq CRUD
    Barcha maydonlarni ko'rsatadi va tahrirlash imkonini beradi
    """

    class Meta:
        model = WritingTask
        fields = [
            'id',
            'test',
            'task_number',
            'task_type',
            'prompt_text',
            'image',
            'instructions',
            'word_limit',
            'time_suggestion',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_task_number(self, value):
        """Task number 1 yoki 2 bo'lishi kerak"""
        if value not in [1, 2]:
            raise serializers.ValidationError("Task number must be 1 or 2")
        return value

    def validate(self, data):
        """
        Bir testda bir xil task_number ikki marta bo'lmasligi kerak
        (faqat yangi yaratishda tekshirish)
        """
        if not self.instance:  # Yangi yaratishda
            test = data.get('test')
            task_number = data.get('task_number')

            if WritingTask.objects.filter(test=test, task_number=task_number).exists():
                raise serializers.ValidationError(
                    f"Task {task_number} already exists for this test"
                )

        return data


class WritingTaskListSerializer(serializers.ModelSerializer):
    """
    Student uchun - faqat o'qish
    Kerakli ma'lumotlarni ko'rsatadi
    """
    test_title = serializers.CharField(source='test.title', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)

    class Meta:
        model = WritingTask
        fields = [
            'id',
            'test',
            'test_title',
            'task_number',
            'task_type',
            'task_type_display',
            'prompt_text',
            'image',
            'instructions',
            'word_limit',
            'time_suggestion'
        ]
        read_only_fields = fields  # Barcha maydonlar faqat o'qish uchun


class WritingTaskDetailSerializer(serializers.ModelSerializer):
    """
    Student bitta taskni to'liq ko'rishi uchun
    """
    test_title = serializers.CharField(source='test.title', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)

    class Meta:
        model = WritingTask
        fields = [
            'id',
            'test',
            'test_title',
            'task_number',
            'task_type',
            'task_type_display',
            'prompt_text',
            'image',
            'instructions',
            'word_limit',
            'time_suggestion',
            'created_at'
        ]