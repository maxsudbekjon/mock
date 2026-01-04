from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from rest_framework.exceptions import ValidationError


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

    question_number = models.IntegerField(blank=True, null=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    question_data = models.JSONField(
        blank=True,
        null=True,
        help_text="""
        Multiple Choice: {"options": ["A) London", "B) Paris"]}
        Matching: {"left": ["1. Dog"], "right": ["A. Barks"]}
        Table: {"headers": ["Name"], "rows": [["___"]]} (ixtiyoriy - rasm bo'lsa kerak emas)
        Completion: {"word_limit": 2} or {}
        """
    )

    question_image = models.ImageField(
        upload_to='listening/questions/',
        blank=True,
        null=True,
        help_text='Table/Map/Diagram uchun rasm, qolganlariga ixtiyoriy'
    )

    points = models.IntegerField(default=1)

    class Meta:
        db_table = 'listening_questions'
        ordering = ['question_number']
        unique_together = ['section', 'question_number']

    def __str__(self):
        return f"Q{self.question_number} ({self.get_question_type_display()})"

    def save(self, *args, **kwargs):
        """question_number ni avtomatik hisoblaydigan"""
        if self.question_number is None:
            # Shu sectiondagi oxirgi raqamni topish
            last_question = ListeningQuestion.objects.filter(
                section=self.section
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
            if not self.question_data or 'left' not in self.question_data or 'right' not in self.question_data:
                raise ValidationError({
                    'question_data': 'Matching uchun "left" va "right" kerak'
                })

        elif self.question_type == 'table':
            has_data = self.question_data and 'headers' in self.question_data and 'rows' in self.question_data
            has_image = bool(self.question_image)

            if not has_data and not has_image:
                raise ValidationError(
                    'Table uchun question_data (headers, rows) yoki question_image kerak'
                )

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
        """Table structure - xatolikni oldini olish uchun"""
        if self.question_type == 'table' and self.question_data:
            headers = self.question_data.get('headers', [])
            rows = self.question_data.get('rows', [])

            # None bo'lsa bo'sh list qaytarish
            return {
                'headers': headers if headers is not None else [],
                'rows': rows if rows is not None else []
            }
        return {'headers': [], 'rows': []}

    @property
    def word_limit(self):
        """Word limit for completion"""
        if self.question_type == 'completion' and self.question_data:
            return self.question_data.get('word_limit')
        return None



