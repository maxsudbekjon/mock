
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
    fields = ['question_number', 'question_text', 'question_type', 'question_data', 'correct_answer', 'points']
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
        'id',
        'section',
        'question_number',
        'question_type_icon',
        'question_preview',
        'correct_answer_preview',
        'points'
    ]
    list_filter = ['section__test', 'section', 'question_type']
    search_fields = ['question_text', 'question_number']
    ordering = ['section', 'question_number']

    list_editable = ['points']  # Points ni to'g'ridan-to'g'ri edit qilish

    fieldsets = (
        ('Basic Info', {
            'fields': ('section', 'question_number', 'question_type')
        }),
        ('Question', {
            'fields': ('question_text', 'question_data'),
            'description': '''
                <b>Question Data formatlar:</b><br>
                • Multiple Choice: {"options": ["A) London", "B) Paris", "C) Berlin"]}<br>
                • Matching: {"left": ["1. Dog", "2. Cat"], "right": ["A. Barks", "B. Meows"]}<br>
                • Table: {"headers": ["Name", "Age"], "rows": [["___", "25"], ["Bob", "___"]]}<br>
                • Completion: {"word_limit": 2} yoki {} (bo'sh)
            '''
        }),
        ('Answer', {
            'fields': ('correct_answer', 'points'),
            'description': '''
                <b>Correct Answer formatlar:</b><br>
                • Multiple Choice: "A" yoki "B"<br>
                • Completion: "London" yoki ["word1", "word2"]<br>
                • Matching: {"1": "B", "2": "A"}<br>
                • Table: {"0-0": "Alice", "1-1": "28"}
            '''
        }),
    )

    def question_type_icon(self, obj):
        """Question type ni icon bilan ko'rsatish"""
        icons = {
            'multiple_choice': '🔘',
            'completion': '✏️',
            'matching': '🔗',
            'table': '📊'
        }
        icon = icons.get(obj.question_type, '❓')
        return format_html(
            '<span style="font-size: 20px;" title="{}">{}</span>',
            obj.get_question_type_display(),
            icon
        )

    question_type_icon.short_description = 'Type'

    def question_preview(self, obj):
        """Savol matni preview"""
        text = obj.question_text
        if len(text) > 60:
            return format_html('<span title="{}">{}</span>', text, text[:60] + "...")
        return text

    question_preview.short_description = 'Question'

    def correct_answer_preview(self, obj):
        """To'g'ri javobni qisqacha ko'rsatish"""
        answer = obj.correct_answer

        # Dict yoki list bo'lsa, qisqartirish
        if isinstance(answer, (dict, list)):
            answer_str = str(answer)
            if len(answer_str) > 30:
                return format_html(
                    '<span style="color: green; font-family: monospace;" title="{}">{}</span>',
                    answer_str,
                    answer_str[:30] + "..."
                )
            return format_html(
                '<span style="color: green; font-family: monospace;">{}</span>',
                answer_str
            )

        # Oddiy string
        return format_html(
            '<span style="color: green; font-weight: bold;">{}</span>',
            str(answer)
        )

    correct_answer_preview.short_description = 'Correct Answer'

    # Readonly fields - ma'lumot ko'rish uchun
    readonly_fields = ['options_display', 'matching_display', 'table_display', 'word_limit_display']

    def options_display(self, obj):
        """Multiple choice options ni ko'rsatish"""
        if obj.question_type == 'multiple_choice':
            options = obj.options
            if options:
                html = '<ul style="margin: 0; padding-left: 20px;">'
                for option in options:
                    html += f'<li>{option}</li>'
                html += '</ul>'
                return format_html(html)
        return '-'

    options_display.short_description = 'Options (Preview)'

    def matching_display(self, obj):
        """Matching pairs ni ko'rsatish"""
        if obj.question_type == 'matching':
            pairs = obj.matching_pairs
            if pairs['left'] and pairs['right']:
                html = '<div style="display: flex; gap: 40px;">'
                html += '<div><b>Left:</b><ul style="margin: 5px 0; padding-left: 20px;">'
                for item in pairs['left']:
                    html += f'<li>{item}</li>'
                html += '</ul></div>'
                html += '<div><b>Right:</b><ul style="margin: 5px 0; padding-left: 20px;">'
                for item in pairs['right']:
                    html += f'<li>{item}</li>'
                html += '</ul></div>'
                html += '</div>'
                return format_html(html)
        return '-'

    matching_display.short_description = 'Matching Pairs (Preview)'

    def table_display(self, obj):
        """Table structure ni ko'rsatish"""
        if obj.question_type == 'table':
            structure = obj.table_structure
            if structure['headers'] and structure['rows']:
                html = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">'
                html += '<thead><tr>'
                for header in structure['headers']:
                    html += f'<th style="background: #f0f0f0; padding: 5px;">{header}</th>'
                html += '</tr></thead><tbody>'
                for row in structure['rows']:
                    html += '<tr>'
                    for cell in row:
                        style = 'padding: 5px;'
                        if cell == '___':
                            style += ' background: #ffffcc; font-weight: bold;'
                        html += f'<td style="{style}">{cell}</td>'
                    html += '</tr>'
                html += '</tbody></table>'
                return format_html(html)
        return '-'

    table_display.short_description = 'Table Structure (Preview)'

    def word_limit_display(self, obj):
        """Word limit ni ko'rsatish"""
        if obj.question_type == 'completion':
            limit = obj.word_limit
            if limit:
                return format_html(
                    '<span style="color: blue; font-weight: bold;">{} words max</span>',
                    limit
                )
            return 'No limit'
        return '-'

    word_limit_display.short_description = 'Word Limit'

    def get_fieldsets(self, request, obj=None):
        """Fieldsets ni question type ga qarab o'zgartirish"""
        fieldsets = list(super().get_fieldsets(request, obj))

        if obj:  # Edit rejimida
            # Preview fieldlarni qo'shish
            if obj.question_type == 'multiple_choice':
                fieldsets.append((
                    'Preview',
                    {'fields': ('options_display',)}
                ))
            elif obj.question_type == 'matching':
                fieldsets.append((
                    'Preview',
                    {'fields': ('matching_display',)}
                ))
            elif obj.question_type == 'table':
                fieldsets.append((
                    'Preview',
                    {'fields': ('table_display',)}
                ))
            elif obj.question_type == 'completion':
                fieldsets.append((
                    'Preview',
                    {'fields': ('word_limit_display',)}
                ))

        return fieldsets


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


