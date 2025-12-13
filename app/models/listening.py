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


from django.db import models
from django.core.exceptions import ValidationError


class ListeningQuestion(models.Model):
    """Listening section savollari"""

    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('completion', 'Completion'),
        ('matching', 'Matching'),
        ('table', 'Table Completion'),
    ]

    section = models.ForeignKey(
        'ListeningSection',
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_number = models.IntegerField()
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    # Barcha qo'shimcha ma'lumotlar shu fieldda
    question_data = models.JSONField(
        blank=True,
        null=True,
        help_text="""
        Multiple Choice: {"options": ["A) London", "B) Paris"]}
        Matching: {"left": ["1. Dog"], "right": ["A. Barks"]}
        Table: {"headers": ["Name"], "rows": [["___"]]}
        Completion: {"word_limit": 2} or {}
        """
    )

    # To'g'ri javob - barcha typelar uchun bitta field
    correct_answer = models.JSONField(
        help_text="""
        Multiple Choice: "A"
        Completion: "London" or ["word1", "word2"]
        Matching: {"1": "B", "2": "A"}
        Table: {"0-0": "Alice", "1-1": "30"}
        """
    )

    points = models.IntegerField(default=1)

    class Meta:
        db_table = 'listening_questions'
        ordering = ['question_number']
        unique_together = ['section', 'question_number']

    def __str__(self):
        return f"Q{self.question_number} ({self.get_question_type_display()})"

    def clean(self):
        """Validation"""
        if self.question_type == 'multiple_choice':
            if not self.question_data or 'options' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Multiple choice uchun "options" kerak'
                })

        elif self.question_type == 'matching':
            if not self.question_data or 'left' not in self.question_data or 'right' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Matching uchun "left" va "right" kerak'
                })

        elif self.question_type == 'table':
            if not self.question_data or 'headers' not in self.question_data or 'rows' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Table uchun "headers" va "rows" kerak'
                })

    # def check_answer(self, user_answer):
    #     """Javobni tekshirish"""
    #     import re
    #
    #     if self.question_type == 'multiple_choice':
    #         return str(user_answer).strip().upper() == str(self.correct_answer).strip().upper()
    #
    #     elif self.question_type == 'completion':
    #         def normalize(text):
    #             return re.sub(r'[^\w\s]', '', str(text).lower()).strip()
    #
    #         if isinstance(self.correct_answer, list):
    #             if not isinstance(user_answer, list):
    #                 return False
    #             return all(normalize(ua) == normalize(ca) for ua, ca in zip(user_answer, self.correct_answer))
    #
    #         return normalize(user_answer) == normalize(self.correct_answer)
    #
    #     elif self.question_type == 'matching':
    #         return isinstance(user_answer, dict) and user_answer == self.correct_answer
    #
    #     elif self.question_type == 'table':
    #         if not isinstance(user_answer, dict):
    #             return False
    #
    #         def normalize(text):
    #             return re.sub(r'[^\w\s]', '', str(text).lower()).strip()
    #
    #         for key, correct_val in self.correct_answer.items():
    #             if normalize(user_answer.get(key, '')) != normalize(correct_val):
    #                 return False
    #         return True
    #
    #     return False

    @property
    def options(self):
        """Multiple choice options"""
        if self.question_type == 'multiple_choice' and self.question_data:
            return self.question_data.get('options', [])
        return []

    @property
    def matching_pairs(self):
        """Matching pairs"""
        if self.question_type == 'matching' and self.question_data:
            return {
                'left': self.question_data.get('left', []),
                'right': self.question_data.get('right', [])
            }
        return {'left': [], 'right': []}

    @property
    def table_structure(self):
        """Table structure"""
        if self.question_type == 'table' and self.question_data:
            return {
                'headers': self.question_data.get('headers', []),
                'rows': self.question_data.get('rows', [])
            }
        return {'headers': [], 'rows': []}

    @property
    def word_limit(self):
        """Word limit for completion"""
        if self.question_type == 'completion' and self.question_data:
            return self.question_data.get('word_limit')
        return None


# class ListeningQuestion(models.Model):
#     """Listening section savollari"""
#
#     QUESTION_TYPE_CHOICES = [
#         ('multiple_choice', 'Multiple Choice'),
#         ('completion', 'Completion'),
#         ('matching', 'Matching'),
#         ('table', 'Table Completion'),
#     ]
#
#     section = models.ForeignKey(ListeningSection, on_delete=models.CASCADE, related_name='questions')
#     question_number = models.IntegerField()
#
#     question_text = models.TextField()
#     question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
#
#     # Options (faqat 'options' type uchun)
#     # Example: ["A) London", "B) Paris", "C) Berlin", "D) Rome"]
#     options = models.JSONField(blank=True, null=True, help_text="Required for 'options' type")
#
#     correct_answer = models.CharField(max_length=255)
#     points = models.IntegerField(default=1)
#
#     # Metadata
#     # explanation = models.TextField(blank=True, help_text="Answer explanation for students")
#
#     class Meta:
#         db_table = 'listening_questions'
#         ordering = ['question_number']
#         unique_together = ['section', 'question_number']
#
#     def __str__(self):
#         return f"Q{self.question_number}: {self.question_text[:50]}"
#
#     def clean(self):
#         """Validate that options are provided for 'options' type"""
#         from django.core.exceptions import ValidationError
#         if self.question_type == 'options' and not self.options:
#             raise ValidationError("Options are required for multiple choice questions")

