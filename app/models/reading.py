from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .listening import Test


class ReadingPassage(models.Model):
    """Reading passages - har bir testda 3 ta passage"""

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='reading_passages')
    passage_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])

    title = models.CharField(max_length=255)
    passage_text = models.TextField(help_text="Full reading passage text")

    # Optional metadata
    word_count = models.IntegerField(blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, help_text="Source of the passage")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reading_passages'
        unique_together = ['test', 'passage_number']
        ordering = ['passage_number']

    def __str__(self):
        return f"{self.test.title} - Passage {self.passage_number}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-calculate word count
        if self.passage_text:
            self.word_count = len(self.passage_text.split())
        super().save(*args, **kwargs)


class ReadingQuestion(models.Model):
    """Reading passage savollari"""

    QUESTION_TYPE_CHOICES = [
        ('written', 'Written Answer'),  # Yozma javob
        ('options', 'Multiple Choice'),  # Variantlar
    ]

    passage = models.ForeignKey(ReadingPassage, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()

    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    # Options (faqat 'options' type uchun)
    options = models.JSONField(blank=True, null=True, help_text="Required for 'options' type")

    correct_answer = models.CharField(max_length=500)
    points = models.IntegerField(default=1)

    # Metadata
    explanation = models.TextField(blank=True)

    class Meta:
        db_table = 'reading_questions'
        ordering = ['question_number']
        unique_together = ['passage', 'question_number']

    def __str__(self):
        return f"Q{self.question_number}: {self.question_text[:50]}"

    def clean(self):
        """Validate that options are provided for 'options' type"""
        from django.core.exceptions import ValidationError
        if self.question_type == 'options' and not self.options:
            raise ValidationError("Options are required for multiple choice questions")