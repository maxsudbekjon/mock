from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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
    # transcript = models.TextField(blank=True, help_text="Audio transcript (optional)")

    # Instructions
    instructions = models.TextField(blank=True)

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