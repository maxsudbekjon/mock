from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone



class Test(models.Model):
    """Main Test model"""

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='intermediate')
    is_published = models.BooleanField(default=False)

    # Vaqt chegaralari (daqiqalarda)
    # listening_duration = models.IntegerField(default=30, help_text="Listening vaqti (daqiqa)")
    # reading_duration = models.IntegerField(default=60, help_text="Reading vaqti (daqiqa)")
    # writing_duration = models.IntegerField(default=60, help_text="Writing vaqti (daqiqa)")

    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tests'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ListeningSection(models.Model):
    """Listening section - har bir testda 4 ta section"""

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='listening_sections')
    section_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])

    # Audio
    audio_file = models.FileField(upload_to='listening/audios/')
    audio_duration = models.IntegerField(help_text="Duration in seconds")

    # Instructions
    instructions = models.TextField(blank=True)

    # # Har bir qism uchun boshlanish vaqti
    # listening_started_at = models.DateTimeField(null=True, blank=True)
    # reading_started_at = models.DateTimeField(null=True, blank=True)
    # writing_started_at = models.DateTimeField(null=True, blank=True)
    #
    # # Har bir qism uchun tugash vaqti
    # listening_completed_at = models.DateTimeField(null=True, blank=True)
    # reading_completed_at = models.DateTimeField(null=True, blank=True)
    # writing_completed_at = models.DateTimeField(null=True, blank=True)
    #
    # def get_remaining_time(self, section_type):
    #     """Qolgan vaqtni hisoblash (soniyalarda)"""
    #     if section_type == 'listening':
    #         started = self.listening_started_at
    #         duration = self.test.listening_duration * 60  # daqiqadan soniyaga
    #     elif section_type == 'reading':
    #         started = self.reading_started_at
    #         duration = self.test.reading_duration * 60
    #     elif section_type == 'writing':
    #         started = self.writing_started_at
    #         duration = self.test.writing_duration * 60
    #     else:
    #         return None
    #
    #     if not started:
    #         return duration  # Hali boshlanmagan
    #
    #     elapsed = (timezone.now() - started).total_seconds()
    #     remaining = duration - elapsed
    #
    #     return max(0, int(remaining))  # Manfiy bo'lmasin
    #
    # def is_section_expired(self, section_type):
    #     """Section vaqti tugaganmi?"""
    #     return self.get_remaining_time(section_type) == 0

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listening_sections'
        unique_together = ['test', 'section_number']
        ordering = ['section_number']

    def __str__(self):
        return f"{self.test.title} - Section {self.section_number}"


class ListeningQuestion(models.Model):
    """Listening section savollari"""

    QUESTION_TYPE_CHOICES = [
        ('written', 'Written Answer'),  # Yozma javob
        ('options', 'Multiple Choice'),  # Variantlar
    ]

    section = models.ForeignKey(ListeningSection, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()

    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    # Options (faqat 'options' type uchun)
    # Example: ["A) London", "B) Paris", "C) Berlin", "D) Rome"]
    options = models.JSONField(blank=True, null=True, help_text="Required for 'options' type")

    correct_answer = models.CharField(max_length=255)
    points = models.IntegerField(default=1)

    # Metadata
    # explanation = models.TextField(blank=True, help_text="Answer explanation for students")

    class Meta:
        db_table = 'listening_questions'
        ordering = ['question_number']
        unique_together = ['section', 'question_number']

    def __str__(self):
        return f"Q{self.question_number}: {self.question_text[:50]}"

    def clean(self):
        """Validate that options are provided for 'options' type"""
        from django.core.exceptions import ValidationError
        if self.question_type == 'options' and not self.options:
            raise ValidationError("Options are required for multiple choice questions")