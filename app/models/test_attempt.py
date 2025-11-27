
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator



class TestAttempt(models.Model):
    """Student test attempts"""

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='attempts')

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')

    # Scores
    listening_score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    reading_score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    writing_score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    overall_band_score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)

    # Metadata
    time_spent = models.IntegerField(default=0, help_text="Time spent in seconds")
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'test_attempts'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.status})"

    def calculate_overall_score(self):
        """Calculate overall band score from individual sections"""
        scores = [s for s in [self.listening_score, self.reading_score, self.writing_score] if s is not None]

        if not scores:
            return None

        average = sum(scores) / len(scores)

        # Round to nearest 0.5
        self.overall_band_score = round(average * 2) / 2
        self.save()

        return self.overall_band_score


class ListeningAnswer(models.Model):
    """Student listening answers"""

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='listening_answers')
    question = models.ForeignKey('ListeningQuestion', on_delete=models.CASCADE)

    user_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    answered_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.IntegerField(default=0, help_text="Time spent on this question in seconds")

    class Meta:
        db_table = 'listening_answers'
        unique_together = ['attempt', 'question']

    def check_answer(self):
        """Check if answer is correct"""
        # Case-insensitive comparison, strip whitespace
        user_ans = self.user_answer.strip().lower()
        correct_ans = self.question.correct_answer.strip().lower()

        self.is_correct = (user_ans == correct_ans)
        self.save()

        return self.is_correct

    def __str__(self):
        return f"Q{self.question.question_number}: {self.user_answer} ({'✓' if self.is_correct else '✗'})"


class ReadingAnswer(models.Model):
    """Student reading answers"""

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='reading_answers')
    question = models.ForeignKey('ReadingQuestion', on_delete=models.CASCADE)

    user_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    answered_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.IntegerField(default=0)

    class Meta:
        db_table = 'reading_answers'
        unique_together = ['attempt', 'question']

    def check_answer(self):
        """Check if answer is correct"""
        user_ans = self.user_answer.strip().lower()
        correct_ans = self.question.correct_answer.strip().lower()

        self.is_correct = (user_ans == correct_ans)
        self.save()

        return self.is_correct

    def __str__(self):
        return f"Q{self.question.question_number}: {self.user_answer} ({'✓' if self.is_correct else '✗'})"


class WritingSubmission(models.Model):
    """Student writing submissions"""

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='writing_submissions')
    task = models.ForeignKey('WritingTask', on_delete=models.CASCADE)

    submission_text = models.TextField()
    word_count = models.IntegerField()

    submitted_at = models.DateTimeField(auto_now_add=True)

    # Teacher grading
    graded_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_writings')

    # IELTS Writing criteria scores (0-9)
    task_achievement = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )
    coherence_cohesion = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )
    lexical_resource = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )
    grammatical_accuracy = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )

    overall_score = models.DecimalField(max_digits=2, decimal_places=1, blank=True, null=True)

    teacher_feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'writing_submissions'
        unique_together = ['attempt', 'task']

    def save(self, *args, **kwargs):
        # Auto-calculate word count
        if self.submission_text:
            self.word_count = len(self.submission_text.split())
        super().save(*args, **kwargs)

    def calculate_overall_score(self):
        """Calculate overall writing score from criteria"""
        scores = [
            self.task_achievement,
            self.coherence_cohesion,
            self.lexical_resource,
            self.grammatical_accuracy
        ]

        if all(s is not None for s in scores):
            average = sum(scores) / 4
            # Round to nearest 0.5
            self.overall_score = round(average * 2) / 2
            self.save()

            return self.overall_score

        return None

    def __str__(self):
        return f"Task {self.task.task_number} - {self.word_count} words"