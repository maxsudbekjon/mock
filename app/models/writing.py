from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .listening import Test


class WritingTask(models.Model):
    """Writing tasks - har bir testda 2 ta task"""

    TASK_TYPE_CHOICES = [
        ('data_description', 'Describe Data/Graph/Chart'),
        ('letter', 'Letter Writing'),
        ('essay', 'Essay'),
        ('report', 'Report'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='writing_tasks')
    task_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(2)])

    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    prompt_text = models.TextField(help_text="Task prompt/question")

    # Task 1 uchun chart image
    image = models.ImageField(upload_to='writing/charts/', blank=True, null=True)

    instructions = models.TextField(blank=True)
    word_limit = models.IntegerField(help_text="Minimum word count (150 or 250)")
    time_suggestion = models.IntegerField(help_text="Suggested time in minutes (20 or 40)")

    # Sample answer (optional)
    # sample_answer = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'writing_tasks'
        unique_together = ['test', 'task_number']
        ordering = ['task_number']

    def __str__(self):
        return f"{self.test.title} - Task {self.task_number}"