# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ==================== TEST ATTEMPT ====================
class TestAttempt(models.Model):
    """Student test urinishlari - barcha sectionlarni birlashtiruvchi"""

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='attempts')

    # Vaqt tracking
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')

    # Band scores (Teacher tomonidan qo'yiladi)
    listening_band = models.DecimalField(
        max_digits=2, decimal_places=1,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        help_text="Listening band score 0-9"
    )
    reading_band = models.DecimalField(
        max_digits=2, decimal_places=1,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        help_text="Reading band score 0-9"
    )
    writing_band = models.DecimalField(
        max_digits=2, decimal_places=1,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        help_text="Writing band score 0-9"
    )
    overall_band = models.DecimalField(
        max_digits=2, decimal_places=1,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        help_text="Overall band score"
    )

    # Teacher info
    teacher_comment = models.TextField(blank=True, help_text="Teacher umumiy sharhi")
    graded_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_attempts'
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    listening_submitted = models.BooleanField(default=False)
    listening_submitted_at = models.DateTimeField(null=True, blank=True)

    reading_submitted = models.BooleanField(default=False)
    reading_submitted_at = models.DateTimeField(null=True, blank=True)

    writing_submitted = models.BooleanField(default=False)
    writing_submitted_at = models.DateTimeField(null=True, blank=True)

    # Section start times (vaqt hisoblash uchun)
    listening_started_at = models.DateTimeField(null=True, blank=True)
    reading_started_at = models.DateTimeField(null=True, blank=True)
    writing_started_at = models.DateTimeField(null=True, blank=True)

    def all_sections_submitted(self):
        """Barcha sectionlar submitted bo'lganini tekshirish"""
        return all([
            self.listening_submitted,
            self.reading_submitted,
            self.writing_submitted
        ])

    class Meta:
        db_table = 'test_attempts'
        ordering = ['-started_at']
        unique_together = ['user', 'test']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['test', 'status']),
            models.Index(fields=['graded_at']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.test.title} ({self.status})"

    def mark_completed(self):
        """Testni completed deb belgilash"""
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])

    def is_graded(self):
        """Baholangan yoki yo'qligini tekshirish"""
        return self.graded_at is not None

    def calculate_overall_band(self):
        """Umumiy band score ni hisoblash"""
        bands = [
            self.listening_band,
            self.reading_band,
            self.writing_band
        ]

        # Barcha band scorelar mavjud bo'lsa
        if all(band is not None for band in bands):
            average = sum(bands) / 3
            # IELTS rounding: nearest 0.5
            self.overall_band = round(average * 2) / 2
            return self.overall_band

        return None


# ==================== LISTENING ANSWERS ====================
class ListeningAnswer(models.Model):
    """Listening javoblari"""

    attempt = models.ForeignKey(
        TestAttempt,
        on_delete=models.CASCADE,
        related_name='listening_answers'
    )
    question = models.ForeignKey(
        'ListeningQuestion',
        on_delete=models.CASCADE
    )

    # Student javobi
    user_answer = models.CharField(max_length=500, blank=True)

    # Vaqt
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listening_answers'
        unique_together = ['attempt', 'question']
        ordering = ['question__question_number']

    def __str__(self):
        return f"Q{self.question.question_number}: {self.user_answer}"


# ==================== READING ANSWERS ====================
class ReadingAnswer(models.Model):
    """Reading javoblari"""

    attempt = models.ForeignKey(
        TestAttempt,
        on_delete=models.CASCADE,
        related_name='reading_answers'
    )
    question = models.ForeignKey(
        'ReadingQuestion',
        on_delete=models.CASCADE
    )

    # Student javobi
    user_answer = models.CharField(max_length=500, blank=True)

    # Vaqt
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reading_answers'
        unique_together = ['attempt', 'question']
        ordering = ['question__question_number']

    def __str__(self):
        return f"Q{self.question.question_number}: {self.user_answer}"


# ==================== WRITING SUBMISSION ====================
class WritingSubmission(models.Model):
    """Writing javoblari - Task 1 va Task 2"""

    attempt = models.ForeignKey(
        TestAttempt,
        on_delete=models.CASCADE,
        related_name='writing_submissions'
    )
    task = models.ForeignKey(
        'WritingTask',
        on_delete=models.CASCADE
    )

    # Student javobi
    submission_text = models.TextField(blank=True)
    word_count = models.IntegerField(default=0)

    # Vaqt
    submitted_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.IntegerField(default=0, help_text="Sekundlarda")

    class Meta:
        db_table = 'writing_submissions'
        unique_together = ['attempt', 'task']
        ordering = ['task__task_number']
        indexes = [
            models.Index(fields=['submitted_at']),
        ]

    def save(self, *args, **kwargs):
        """Word count avtomatik hisoblash"""
        if self.submission_text:
            self.word_count = len(self.submission_text.split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Task {self.task.task_number} - {self.word_count} words"