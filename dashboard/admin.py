from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from app.models import TestAttempt, ListeningAnswer, ReadingAnswer, WritingSubmission


# ==================== INLINE CLASSES ====================
class ListeningAnswerInline(admin.TabularInline):
    """Listening answers inline"""
    model = ListeningAnswer
    extra = 0
    readonly_fields = ['question', 'user_answer', 'answered_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ReadingAnswerInline(admin.TabularInline):
    """Reading answers inline"""
    model = ReadingAnswer
    extra = 0
    readonly_fields = ['question', 'user_answer', 'answered_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class WritingSubmissionInline(admin.StackedInline):
    """Writing submissions inline"""
    model = WritingSubmission
    extra = 0
    readonly_fields = ['task', 'word_count', 'submitted_at', 'time_spent']
    fields = ['task', 'submission_text', 'word_count', 'submitted_at', 'time_spent']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ==================== TEST ATTEMPT ADMIN ====================
@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    # Ro'yxatda ko'rinadigan ustunlar
    list_display = (
        'user',
        'test',
        'status',
        'overall_band',
        'started_at',
        'is_graded_status'
    )

    # Filtrlash paneli (o'ng tomonda)
    list_filter = ('status', 'test', 'started_at', 'graded_at')

    # Qidiruv maydonlari
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'test__title')

    # O'zgartirib bo'lmaydigan (faqat o'qish uchun) maydonlar
    readonly_fields = ('started_at', 'completed_at', 'created_at', 'updated_at')

    # Formada maydonlarni mantiqiy guruhlarga bo'lish
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'test', 'status')
        }),
        ('Vaqt ko\'rsatkichlari', {
            'fields': ('started_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)  # Bu qismni yashirib qo'yish imkonini beradi
        }),
        ('Natijalar (Band Scores)', {
            'fields': (
                ('listening_band', 'reading_band', 'writing_band'),
                'overall_band'
            )
        }),
        ('Tekshiruvchi (Teacher) ma\'lumotlari', {
            'fields': ('teacher_comment', 'graded_by', 'graded_at')
        }),
        ('Section holatlari', {
            'description': 'Har bir section topshirilganligi haqida ma\'lumot',
            'fields': (
                ('listening_submitted', 'listening_submitted_at'),
                ('reading_submitted', 'reading_submitted_at'),
                ('writing_submitted', 'writing_submitted_at')
            )
        }),
    )

    # Custom ustun: Baholanganligini ko'rsatish uchun
    def is_graded_status(self, obj):
        return obj.is_graded()

    is_graded_status.boolean = True
    is_graded_status.short_description = 'Graded'

    # Model ichidagi overall scoreni hisoblash funksiyasini saqlashdan oldin chaqirish (ixtiyoriy)
    def save_model(self, request, obj, form, change):
        if obj.listening_band and obj.reading_band and obj.writing_band:
            obj.calculate_overall_band()
        super().save_model(request, obj, form, change)


# ==================== LISTENING ANSWER ADMIN ====================
@admin.register(ListeningAnswer)
class ListeningAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'attempt_info',
        'question_number',
        'user_answer',
        'answered_at'
    ]

    list_filter = [
        'answered_at',
        'attempt__status'
    ]

    search_fields = [
        'attempt__user__username',
        'attempt__user__first_name',
        'attempt__user__last_name',
        'user_answer'
    ]

    readonly_fields = ['attempt', 'question', 'answered_at']

    def attempt_info(self, obj):
        """Attempt ma'lumotlari"""
        url = reverse('admin:app_testattempt_change', args=[obj.attempt.id])
        return format_html(
            '<a href="{}">{} - {}</a>',
            url,
            obj.attempt.user.get_full_name(),
            obj.attempt.test.title
        )

    attempt_info.short_description = 'Attempt'

    def question_number(self, obj):
        """Savol raqami"""
        return f"Q{obj.question.question_number}"

    question_number.short_description = 'Question'


# ==================== READING ANSWER ADMIN ====================
@admin.register(ReadingAnswer)
class ReadingAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'attempt_info',
        'question_number',
        'user_answer',
        'answered_at'
    ]

    list_filter = [
        'answered_at',
        'attempt__status'
    ]

    search_fields = [
        'attempt__user__username',
        'attempt__user__first_name',
        'attempt__user__last_name',
        'user_answer'
    ]

    readonly_fields = ['attempt', 'question', 'answered_at']

    def attempt_info(self, obj):
        """Attempt ma'lumotlari"""
        url = reverse('admin:app_testattempt_change', args=[obj.attempt.id])
        return format_html(
            '<a href="{}">{} - {}</a>',
            url,
            obj.attempt.user.get_full_name(),
            obj.attempt.test.title
        )

    attempt_info.short_description = 'Attempt'

    def question_number(self, obj):
        """Savol raqami"""
        return f"Q{obj.question.question_number}"

    question_number.short_description = 'Question'


# ==================== WRITING SUBMISSION ADMIN ====================
@admin.register(WritingSubmission)
class WritingSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'attempt_info',
        'task_number',
        'word_count_display',
        'time_spent_display',
        'submitted_at'
    ]

    list_filter = [
        'submitted_at',
        'task__task_number',
        'attempt__status'
    ]

    search_fields = [
        'attempt__user__username',
        'attempt__user__first_name',
        'attempt__user__last_name',
        'submission_text'
    ]

    readonly_fields = [
        'attempt',
        'task',
        'word_count',
        'submitted_at',
        'time_spent'
    ]

    fieldsets = (
        ('Submission Info', {
            'fields': ('attempt', 'task')
        }),
        ('Content', {
            'fields': ('submission_text', 'word_count')
        }),
        ('Metadata', {
            'fields': ('submitted_at', 'time_spent')
        })
    )

    def attempt_info(self, obj):
        """Attempt ma'lumotlari"""
        url = reverse('admin:app_testattempt_change', args=[obj.attempt.id])
        return format_html(
            '<a href="{}">{} - {}</a>',
            url,
            obj.attempt.user.get_full_name(),
            obj.attempt.test.title
        )

    attempt_info.short_description = 'Attempt'

    def task_number(self, obj):
        """Task raqami"""
        return f"Task {obj.task.task_number}"

    task_number.short_description = 'Task'

    def word_count_display(self, obj):
        """Word count ko'rsatish"""
        required = 150 if obj.task.task_number == 1 else 250
        color = '#28A745' if obj.word_count >= required else '#DC3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span> / {}',
            color,
            obj.word_count,
            required
        )

    word_count_display.short_description = 'Words'

    def time_spent_display(self, obj):
        """Sarflangan vaqt"""
        minutes = obj.time_spent // 60
        seconds = obj.time_spent % 60
        return f"{minutes}m {seconds}s"

    time_spent_display.short_description = 'Time Spent'