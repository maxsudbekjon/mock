
from django.contrib import admin
from django.utils.html import format_html
from app.models import (
    User, Test,
    ListeningSection, ListeningQuestion,
    ReadingPassage, ReadingQuestion,
    WritingTask
)


# ============================================
# USER ADMIN
# ============================================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']


# ============================================
# TEST ADMIN
# ============================================

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'difficulty_level', 'is_published', 'created_by', 'created_at']
    list_filter = ['difficulty_level', 'is_published', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_published']
    ordering = ['-created_at']

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Yangi test
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================
# LISTENING ADMIN
# ============================================

class ListeningQuestionInline(admin.TabularInline):
    """Inline - Section ichida savollarni ko'rsatish"""
    model = ListeningQuestion
    extra = 1
    fields = ['question_number', 'question_text', 'question_type', 'options', 'correct_answer', 'points']
    ordering = ['question_number']


@admin.register(ListeningSection)
class ListeningSectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'section_number', 'audio_preview', 'audio_duration', 'question_count']
    list_filter = ['test', 'section_number']
    search_fields = ['test__title']
    ordering = ['test', 'section_number']

    inlines = [ListeningQuestionInline]  # Section ochganda savollar ko'rinadi

    def audio_preview(self, obj):
        if obj.audio_file:
            return format_html(
                '<audio controls><source src="{}" type="audio/mpeg"></audio>',
                obj.audio_file.url
            )
        return "No audio"

    audio_preview.short_description = 'Audio'

    def question_count(self, obj):
        return obj.questions.count()

    question_count.short_description = 'Questions'


@admin.register(ListeningQuestion)
class ListeningQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'section', 'question_number', 'question_type', 'question_preview', 'correct_answer', 'points']
    list_filter = ['section__test', 'section', 'question_type']
    search_fields = ['question_text', 'correct_answer']
    ordering = ['section', 'question_number']

    list_editable = ['points']  # Points ni to'g'ridan-to'g'ri edit qilish

    fieldsets = (
        ('Basic Info', {
            'fields': ('section', 'question_number', 'question_type')
        }),
        ('Question', {
            'fields': ('question_text', 'options')
        }),
        ('Answer', {
            'fields': ('correct_answer', 'points')
        }),
    )

    def question_preview(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text

    question_preview.short_description = 'Question'


# ============================================
# READING ADMIN
# ============================================

class ReadingQuestionInline(admin.TabularInline):
    model = ReadingQuestion
    extra = 1
    fields = ['question_number', 'question_text', 'question_type', 'options', 'correct_answer', 'points']
    ordering = ['question_number']


@admin.register(ReadingPassage)
class ReadingPassageAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'passage_number', 'title', 'word_count', 'question_count']
    list_filter = ['test', 'passage_number']
    search_fields = ['title', 'passage_text']
    ordering = ['test', 'passage_number']

    inlines = [ReadingQuestionInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('test', 'passage_number', 'title')
        }),
        ('Passage', {
            'fields': ('passage_text',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('word_count', 'source'),
            'classes': ('collapse',)
        }),
    )

    def question_count(self, obj):
        return obj.questions.count()

    question_count.short_description = 'Questions'


@admin.register(ReadingQuestion)
class ReadingQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'passage', 'question_number', 'question_type','correct_answer', 'points']
    list_filter = ['passage__test', 'passage', 'question_type']
    search_fields = ['question_text', 'correct_answer']
    ordering = ['passage', 'question_number']
    list_editable = ['points']


# ============================================
# WRITING ADMIN
# ============================================

@admin.register(WritingTask)
class WritingTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'task_number', 'task_type', 'word_limit', 'time_suggestion', 'image_preview']
    list_filter = ['test', 'task_number', 'task_type']
    search_fields = ['prompt_text']
    ordering = ['test', 'task_number']

    fieldsets = (
        ('Basic Info', {
            'fields': ('test', 'task_number', 'task_type')
        }),
        ('Task Content', {
            'fields': ('prompt_text', 'image', 'instructions')
        }),
        ('Requirements', {
            'fields': ('word_limit', 'time_suggestion')
        }),
        # ('Sample Answer', {
        #     'fields': ('sample_answer',),
        #     'classes': ('collapse',)
        # }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "No image"

    image_preview.short_description = 'Image'


