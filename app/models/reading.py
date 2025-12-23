from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .listening import Test
from django.core.exceptions import ValidationError



class ReadingPassage(models.Model):
    """Reading passages - har bir testda 3 ta passage"""

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='reading_passages')
    passage_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])

    title = models.CharField(max_length=255)
    passage_text = models.TextField(help_text="Full reading passage text")

    # Optional metadata
    word_count = models.IntegerField(blank=True, null=True)
    # source = models.CharField(max_length=255, blank=True, help_text="Source of the passage")

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
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False/Not Given'),
        ('yes_no', 'Yes/No/Not Given'),
        ('completion', 'Completion'),
        ('matching', 'Matching'),
        ('short_answer', 'Short Answer'),
    ]

    passage = models.ForeignKey('ReadingPassage', on_delete=models.CASCADE, related_name='questions')
    # question_number ni ixtiyoriy qilish
    question_number = models.IntegerField(blank=True, null=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    question_data = models.JSONField(
        blank=True,
        null=True,
        help_text="""
        Multiple Choice: {"options": ["A) ...", "B) ..."]}
        True/False/Yes/No: {} (bo'sh, options avtomatik)
        Completion: {"word_limit": 2} (ixtiyoriy)
        Matching: {"items": ["1. Heading A", "2. Heading B"], "paragraphs": ["A", "B", "C"]}
        Short Answer: {"word_limit": 3}
        """
    )

    correct_answer = models.JSONField(
        null=True, blank=True,
        help_text="""
        Multiple Choice: "A"
        True/False: "True" or "False" or "Not Given"
        Yes/No: "Yes" or "No" or "Not Given"
        Completion: "answer" or ["answer1", "answer2"]
        Matching: {"1": "C", "2": "A"}
        Short Answer: "answer" or ["answer1", "answer2"]
        """
    )

    points = models.IntegerField(default=1)

    class Meta:
        db_table = 'reading_questions'
        ordering = ['question_number']
        unique_together = ['passage', 'question_number']

    def __str__(self):
        return f"Q{self.question_number} ({self.get_question_type_display()})"

    def save(self, *args, **kwargs):
        """question_number ni avtomatik hisoblaydigan"""
        if self.question_number is None:
            # Shu passagedagi oxirgi raqamni topish
            last_question = ReadingQuestion.objects.filter(
                passage=self.passage
            ).order_by('-question_number').first()

            if last_question and last_question.question_number:
                self.question_number = last_question.question_number + 1
            else:
                self.question_number = 1

        super().save(*args, **kwargs)

    def clean(self):
        """Validation"""
        if self.question_type == 'multiple_choice':
            if not self.question_data or 'options' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Multiple choice uchun "options" kerak'
                })

        elif self.question_type == 'matching':
            if not self.question_data or 'items' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Matching uchun "items" kerak'
                })

    @property
    def options(self):
        """Multiple choice options - NoneType xatoligini oldini olish"""
        if self.question_type == 'multiple_choice' and self.question_data:
            options = self.question_data.get('options', [])
            return options if options is not None else []
        elif self.question_type == 'true_false':
            return ['True', 'False', 'Not Given']
        elif self.question_type == 'yes_no':
            return ['Yes', 'No', 'Not Given']
        return []

    @property
    def matching_items(self):
        """Matching items - NoneType xatoligini oldini olish"""
        if self.question_type == 'matching' and self.question_data:
            items = self.question_data.get('items', [])
            paragraphs = self.question_data.get('paragraphs', [])

            return {
                'items': items if items is not None else [],
                'paragraphs': paragraphs if paragraphs is not None else []
            }
        return {'items': [], 'paragraphs': []}

    @property
    def word_limit(self):
        """Word limit"""
        if self.question_type in ['completion', 'short_answer'] and self.question_data:
            return self.question_data.get('word_limit')
        return None


# class ReadingQuestion(models.Model):
#     """Reading passage savollari"""
#
#     QUESTION_TYPE_CHOICES = [
#         ('written', 'Written Answer'),  # Yozma javob
#         ('options', 'Multiple Choice'),  # Variantlar
#     ]
#
#     passage = models.ForeignKey(ReadingPassage, on_delete=models.CASCADE, related_name='questions')
#     question_number = models.IntegerField()
#
#     question_text = models.TextField()
#     question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
#
#     # Options (faqat 'options' type uchun)
#     options = models.JSONField(blank=True, null=True, help_text="Required for 'options' type")
#
#     correct_answer = models.CharField(max_length=500)
#     points = models.IntegerField(default=1, null=True, blank=True)
#
#     # Metadata
#     # explanation = models.TextField(blank=True)
#
#     class Meta:
#         db_table = 'reading_questions'
#         ordering = ['question_number']
#         unique_together = ['passage', 'question_number']
#
#     def __str__(self):
#         return f"Q{self.question_number}: {self.question_text[:50]}"
#
#     def clean(self):
#         """Validate that options are provided for 'options' type"""
#         from django.core.exceptions import ValidationError
#         if self.question_type == 'options' and not self.options:
#             raise ValidationError("Options are required for multiple choice questions")
