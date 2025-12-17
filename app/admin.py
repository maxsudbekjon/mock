
from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
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
    fields = ['question_number', 'question_text', 'question_type', 'question_data', 'points']
    ordering = ['question_number']

    # JSON fieldlarni to'g'ri ko'rsatish uchun
    readonly_fields = []

    def get_readonly_fields(self, request, obj=None):
        """Inline'da read-only fieldlarni belgilash"""
        if obj:  # Edit rejimida
            return []
        return []


@admin.register(ListeningSection)
class ListeningSectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'section_number', 'audio_preview', 'audio_duration', 'question_count']
    list_filter = ['test', 'section_number']
    search_fields = ['test__title']
    ordering = ['test', 'section_number']

    inlines = [ListeningQuestionInline]  # Section ochganda savollar ko'rinadi

    def audio_preview(self, obj):
        """Audio player"""
        if obj.audio_file:
            return format_html(
                '<audio controls style="width: 300px;"><source src="{}" type="audio/mpeg"></audio>',
                obj.audio_file.url
            )
        return "No audio"

    audio_preview.short_description = 'Audio'

    def question_count(self, obj):
        """Savollar soni"""
        return obj.questions.count()

    question_count.short_description = 'Questions'


@admin.register(ListeningQuestion)
class ListeningQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_number',
        'section',
        'question_type_badge',
        'has_image',
        'points',
        'preview_text'
    ]

    list_filter = [
        'question_type',
        'section',
        'points'
    ]

    search_fields = [
        'question_number',
        'question_text',
        'section__title'
    ]

    ordering = ['section', 'question_number']

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('section', 'question_number', 'question_type', 'points')
        }),
        ('Savol matni', {
            'fields': ('question_text',)
        }),
        ('Qo\'shimcha ma\'lumotlar', {
            'fields': ('question_data', 'question_image'),
            'description': 'Question type ga qarab to\'ldiring'
        }),
    )

    readonly_fields = []

    list_per_page = 50

    # Inline editing
    list_editable = ['points']

    # Actions
    actions = ['duplicate_questions', 'reset_points']

    def question_type_badge(self, obj):
        """Question type ni rangli badge sifatida ko'rsatish"""
        colors = {
            'multiple_choice': '#28a745',
            'completion': '#007bff',
            'matching': '#ffc107',
            'table': '#dc3545'
        }
        color = colors.get(obj.question_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_question_type_display()
        )

    question_type_badge.short_description = 'Type'

    def has_image(self, obj):
        """Rasm borligini ko'rsatish"""
        if obj.question_image:
            return format_html(
                '<span style="color: green; font-size: 16px;">✓</span>'
            )
        return format_html(
            '<span style="color: #ccc; font-size: 16px;">✗</span>'
        )

    has_image.short_description = 'Rasm'

    def preview_text(self, obj):
        """Savol matnini qisqartirib ko'rsatish"""
        text = obj.question_text
        if len(text) > 60:
            return text[:60] + '...'
        return text

    preview_text.short_description = 'Savol matni'

    def save_model(self, request, obj, form, change):
        """Saqlashdan oldin validatsiya"""
        try:
            obj.clean()
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, f'Xatolik: {e}', level='error')
            raise

    def duplicate_questions(self, request, queryset):
        """Tanlangan savollarni nusxalash"""
        count = 0
        for question in queryset:
            question.pk = None
            question.question_number = ListeningQuestion.objects.filter(
                section=question.section
            ).count() + 1
            question.save()
            count += 1

        self.message_user(
            request,
            f'{count} ta savol nusxalandi',
            level='success'
        )

    duplicate_questions.short_description = 'Tanlangan savollarni nusxalash'

    def reset_points(self, request, queryset):
        """Ballni 1 ga qaytarish"""
        updated = queryset.update(points=1)
        self.message_user(
            request,
            f'{updated} ta savol balli 1 ga o\'zgartirildi',
            level='success'
        )

    reset_points.short_description = 'Ballni 1 ga qaytarish'

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)  # ixtiyoriy custom CSS
        }
        js = ('admin/js/question_admin.js',)  # ixtiyoriy custom JS


# ============================================
# READING ADMIN
# ============================================

class ReadingQuestionInline(admin.TabularInline):
    model = ReadingQuestion
    extra = 1
    fields = ['question_number', 'question_text', 'question_type', 'correct_answer', 'points']
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
            'fields': ('word_count', ),
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


