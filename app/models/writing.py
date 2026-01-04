from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .listening import Test


class WritingTask(models.Model):
    """Writing tasks - har bir testda 2 ta task"""

    TASK_TYPE_CHOICES = [
        ('TASK_1', 'Task 1 (Data/Letter)'),
        ('TASK_2', 'Task 2 (Essay)'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='writing_tasks')
    task_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(2)], null=True, blank=True)

    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    prompt_text = models.TextField(help_text="Task prompt/question")

    image = models.ImageField(upload_to='writing/charts/', blank=True, null=True)

    instructions = models.TextField(blank=True)
    word_limit = models.IntegerField(help_text="Minimum word count (150 or 250)", null=True, blank=True)
    time_suggestion = models.IntegerField(help_text="Suggested time in minutes (20 or 40)", null=True, blank=True)



    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'writing_tasks'
        unique_together = ['test', 'task_number']
        ordering = ['task_number']


    def save(self, *args, **kwargs):
        """task_number ni avtomatik ketma-ket hisoblash"""
        if self.task_number is None:
            # Shu testdagi oxirgi task raqamini topish
            last_task = WritingTask.objects.filter(
                test=self.test
            ).order_by('-task_number').first()

            if last_task and last_task.task_number:
                self.task_number = last_task.task_number + 1
            else:
                self.task_number = 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.test.title} - Task {self.task_number}"