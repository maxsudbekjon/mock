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
    list_display = [
        'id',
        'user_info',
        'test_info',
        'status_badge',
        'sections_progress',
        'band_scores',
        'started_at',
        'grading_status'
    ]

    list_filter = [
        'status',
        'listening_submitted',
        'reading_submitted',
        'writing_submitted',
        ('graded_at', admin.EmptyFieldListFilter),
        'started_at',
        'completed_at'
    ]

    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'test__title'
    ]

    readonly_fields = [
        'started_at',
        'completed_at',
        'created_at',
        'updated_at',
        'listening_submitted_at',
        'reading_submitted_at',
        'writing_submitted_at',
        'listening_started_at',
        'reading_started_at',
        'writing_started_at',
        'overall_band_calculated'
    ]

    fieldsets = (
        ('Test Info', {
            'fields': ('user', 'test', 'status')
        }),
        ('Sections Status', {
            'fields': (
                ('listening_submitted', 'listening_submitted_at', 'listening_started_at'),
                ('reading_submitted', 'reading_submitted_at', 'reading_started_at'),
                ('writing_submitted', 'writing_submitted_at', 'writing_started_at'),
            )
        }),
        ('Band Scores', {
            'fields': (
                'listening_band',
                'reading_band',
                'writing_band',
                'overall_band',
                'overall_band_calculated'
            )
        }),
        ('Grading Info', {
            'fields': (
                'teacher_comment',
                'graded_by',
                'graded_at'
            )
        }),
        ('Timestamps', {
            'fields': (
                'started_at',
                'completed_at',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    inlines = [ListeningAnswerInline, ReadingAnswerInline, WritingSubmissionInline]

    actions = ['mark_as_completed', 'calculate_overall_bands']

    def user_info(self, obj):
        """User ma'lumotlari"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.username
        )

    user_info.short_description = 'Student'

    def test_info(self, obj):
        """Test ma'lumotlari"""
        return obj.test.title

    test_info.short_description = 'Test'

    def status_badge(self, obj):
        """Status badge"""
        colors = {
            'in_progress': '#FFA500',  # Orange
            'completed': '#28A745'  # Green
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def sections_progress(self, obj):
        """Sectionlar progressi"""
        sections = [
            ('L', obj.listening_submitted),
            ('R', obj.reading_submitted),
            ('W', obj.writing_submitted)
        ]

        html = []
        for name, submitted in sections:
            color = '#28A745' if submitted else '#DC3545'
            html.append(
                f'<span style="background-color: {color}; color: white; '
                f'padding: 2px 6px; border-radius: 3px; margin: 0 2px;">{name}</span>'
            )

        return format_html(''.join(html))

    sections_progress.short_description = 'Sections'

    def band_scores(self, obj):
        """Band scores"""
        if obj.overall_band:
            return format_html(
                '<strong style="color: #007BFF; font-size: 14px;">Overall: {}</strong><br>'
                '<small>L: {} | R: {} | W: {}</small>',
                obj.overall_band,
                obj.listening_band or '-',
                obj.reading_band or '-',
                obj.writing_band or '-'
            )
        return format_html('<span style="color: #999;">Not graded</span>')

    band_scores.short_description = 'Band Scores'

    def grading_status(self, obj):
        """Baholash holati"""
        if obj.is_graded():
            return format_html(
                '<span style="color: #28A745;">✓ Graded</span><br>'
                '<small>{}</small>',
                obj.graded_at.strftime('%Y-%m-%d %H:%M') if obj.graded_at else ''
            )
        return format_html('<span style="color: #DC3545;">Not graded</span>')

    grading_status.short_description = 'Grading'

    def overall_band_calculated(self, obj):
        """Hisoblangan overall band"""
        band = obj.calculate_overall_band()
        if band:
            return format_html(
                '<strong style="color: #007BFF; font-size: 16px;">{}</strong>',
                band
            )
        return '-'

    overall_band_calculated.short_description = 'Calculated Overall Band'

    # Actions
    @admin.action(description='Mark selected as completed')
    def mark_as_completed(self, request, queryset):
        """Tanlangan testlarni completed deb belgilash"""
        updated = 0
        for attempt in queryset:
            if attempt.status != 'completed':
                attempt.mark_completed()
                updated += 1

        self.message_user(
            request,
            f'{updated} test(s) marked as completed.'
        )

    @admin.action(description='Calculate overall band scores')
    def calculate_overall_bands(self, request, queryset):
        """Overall band scorelarni hisoblash"""
        updated = 0
        for attempt in queryset:
            if attempt.calculate_overall_band():
                attempt.save()
                updated += 1

        self.message_user(
            request,
            f'{updated} overall band score(s) calculated.'
        )


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
        url = reverse('admin:your_app_testattempt_change', args=[obj.attempt.id])
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
        url = reverse('admin:your_app_testattempt_change', args=[obj.attempt.id])
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
        url = reverse('admin:your_app_testattempt_change', args=[obj.attempt.id])
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