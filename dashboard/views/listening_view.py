from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from dashboard.custom_permission import IsTeacherOrAdminOrReadOnly
from app.models import ListeningSection, ListeningQuestion
from dashboard.serializers import ListeningSectionSerializer, ListeningQuestionSerializer




@extend_schema(tags=["Listening_section"])
class ListeningSectionViewSet(viewsets.ModelViewSet):
    """
    Listening Sectionlari bilan ishlash:
    - Audio yuklash (multipart/form-data)
    - Test bo'yicha filterlash
    - Har bir section 1-4 raqamli bo'lishi kerak
    """
    queryset = ListeningSection.objects.all()
    serializer_class = ListeningSectionSerializer
    permission_classes = [IsTeacherOrAdminOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    ordering = ['id']

    def get_queryset(self):
        """Test ID bo'yicha filterlash imkonini beradi: /sections/?test_id=1"""
        queryset = super().get_queryset()
        test_id = self.request.query_params.get('test_id')
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        return queryset

    @extend_schema(
        summary="Sectionlar roʻyxatini olish va Test ID boʻyicha filterlash",
        description="Barcha listening sectionlarni olish. Har bir sectionda savollar soni ko'rsatiladi.",
        parameters=[
            OpenApiParameter(
                name='test_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Sectionlarni maʼlum bir Test ID boʻyicha filterlash uchun.",
                required=False
            )
        ],
        responses={
            200: ListeningSectionSerializer(many=True)
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)






    @extend_schema(
        summary="Bitta Listening Section ma'lumotlarini olish",
        description="Section ID bo'yicha to'liq ma'lumotlarni olish (savollar soni bilan)",
        responses={
            200: ListeningSectionSerializer,
            404: OpenApiExample(
                'Topilmadi',
                value={'detail': 'Not found.'}
            )
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Yangi Listening Section yaratish (audio fayl bilan)",
        description="""
        Yangi listening section yaratish. 
        - Section raqami 1-4 oralig'ida bo'lishi kerak
        - Har bir test uchun section_number unique bo'lishi kerak
        - Audio fayl majburiy
        - Audio duration sekundlarda kiritiladi
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'test': {
                        'type': 'integer',
                        'description': 'Test ID (majburiy)'
                    },
                    'section_number': {
                        'type': 'integer',
                        'description': 'Section raqami (1-4)',
                        'minimum': 1,
                        'maximum': 4
                    },
                    'audio_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Audio fayl (MP3, WAV, va boshqalar) - majburiy'
                    },
                    'audio_duration': {
                        'type': 'integer',
                        'description': 'Audio davomiyligi (sekundlarda) - majburiy',
                        'example': 180
                    },
                    'instructions': {
                        'type': 'string',
                        'description': 'Section uchun ko\'rsatmalar (ixtiyoriy)',
                        'example': 'Listen carefully and answer questions 1-10'
                    }
                },
                'required': ['test', 'section_number', 'audio_file', 'audio_duration']
            }
        },
        examples=[
            OpenApiExample(
                'Listening Section yaratish',
                description='To\'liq ma\'lumotlar bilan yangi section yaratish',
                value={
                    'test': 1,
                    'section_number': 1,
                    'audio_file': '(binary audio file)',
                    'audio_duration': 180,
                    'instructions': 'Listen to the conversation and answer questions 1-10'
                }
            )
        ],
        responses={
            201: ListeningSectionSerializer,
            400: OpenApiExample(
                'Xatolik',
                value={
                    'section_number': ['Ensure this value is less than or equal to 4.'],
                    'test': ['This field is required.']
                }
            )
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Listening Section to'liq yangilash",
        description="""
        Sectionni to'liq yangilash (barcha maydonlar majburiy).
        Audio faylni ham yangilash mumkin.
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'test': {
                        'type': 'integer',
                        'description': 'Test ID'
                    },
                    'section_number': {
                        'type': 'integer',
                        'description': 'Section raqami (1-4)',
                        'minimum': 1,
                        'maximum': 4
                    },
                    'audio_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Yangi audio fayl (ixtiyoriy - yuklmasangiz eski fayl saqlanadi)'
                    },
                    'audio_duration': {
                        'type': 'integer',
                        'description': 'Audio davomiyligi (sekundlarda)'
                    },
                    'instructions': {
                        'type': 'string',
                        'description': 'Section ko\'rsatmalari'
                    }
                },
                'required': ['test', 'section_number', 'audio_duration']
            }
        },
        responses={
            200: ListeningSectionSerializer,
            400: OpenApiExample('Xatolik', value={'detail': 'Validation error'}),
            404: OpenApiExample('Topilmadi', value={'detail': 'Not found.'})
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Listening Section qisman yangilash (PATCH)",
        description="""
        Sectionning faqat kerakli maydonlarini yangilash.
        Masalan, faqat audio faylni yoki faqat instructionsni yangilash mumkin.
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'test': {
                        'type': 'integer',
                        'description': 'Test ID (ixtiyoriy)'
                    },
                    'section_number': {
                        'type': 'integer',
                        'description': 'Section raqami (1-4) (ixtiyoriy)',
                        'minimum': 1,
                        'maximum': 4
                    },
                    'audio_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Yangi audio fayl (ixtiyoriy)'
                    },
                    'audio_duration': {
                        'type': 'integer',
                        'description': 'Audio davomiyligi sekundlarda (ixtiyoriy)'
                    },
                    'instructions': {
                        'type': 'string',
                        'description': 'Yangilangan ko\'rsatmalar (ixtiyoriy)'
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                'Faqat audio yangilash',
                value={
                    'audio_file': '(new audio file)',
                    'audio_duration': 200
                }
            ),
            OpenApiExample(
                'Faqat instructions yangilash',
                value={
                    'instructions': 'Updated instructions text'
                }
            )
        ],
        responses={
            200: ListeningSectionSerializer,
            400: OpenApiExample('Xatolik', value={'detail': 'Validation error'}),
            404: OpenApiExample('Topilmadi', value={'detail': 'Not found.'})
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Listening Section o'chirish",
        description="Section va unga tegishli barcha ma'lumotlarni o'chirish",
        responses={
            204: OpenApiExample('Muvaffaqiyatli o\'chirildi', value=None),
            404: OpenApiExample('Topilmadi', value={'detail': 'Not found.'})
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=['Listening Question'])
class ListeningQuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Listening Questions

    Teachers/Admin: Full CRUD access
    """
    serializer_class = ListeningQuestionSerializer
    permission_classes = [IsTeacherOrAdminOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['section', 'section__test', 'question_type']
    ordering_fields = ['question_number', 'created_at']
    ordering = ['question_number']

    def get_queryset(self):
        """Optimized queryset with select_related"""
        return ListeningQuestion.objects.select_related('section', 'section__test')

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='section',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter questions by section ID',
                required=False
            ),
            OpenApiParameter(
                name='section__test',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter questions by test ID',
                required=False
            ),
            OpenApiParameter(
                name='question_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by question type',
                required=False,
                enum=['multiple_choice', 'completion', 'matching', 'table']
            )
        ],
        description='List all listening questions with optional filtering'
    )
    def list(self, request, *args, **kwargs):
        """List all questions with optional filtering"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'section': {'type': 'integer'},
                    'question_text': {'type': 'string'},
                    'question_type': {
                        'type': 'string',
                        'enum': ['multiple_choice', 'completion', 'matching', 'table']
                    },
                    'question_data': {'type': 'object'},
                    'question_image': {'type': 'string', 'format': 'binary'},
                    # 'correct_answer': {'type': 'string'},
                },
                'required': ['section', 'question_type']
            }
        },
        responses={
            201: ListeningQuestionSerializer,
            400: OpenApiTypes.OBJECT
        },
        description="""
        Create a single listening question.

        Supported question types:
        - multiple_choice: question_data = {"options": ["A) ...", "B) ..."]}
        - completion: question_data = {"word_limit": 2} (optional)
        - matching: question_data = {"left": [...], "right": [...]}
        - table: question_data = {"headers": [...], "rows": [...]} OR question_image

        Note: correct_answer can be a string or JSON object
        """
    )
    def create(self, request, *args, **kwargs):
        """Create a single question"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'section': {'type': 'integer'},
                    # 'question_number': {'type': 'integer'},
                    'question_text': {'type': 'string'},
                    'question_type': {
                        'type': 'string',
                        'enum': ['multiple_choice', 'completion', 'matching', 'table']
                    },
                    'question_data': {'type': 'object'},
                    'question_image': {'type': 'string', 'format': 'binary'},
                    # 'correct_answer': {'type': 'object'},
                }
            }
        },
        responses={
            200: ListeningQuestionSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def update(self, request, *args, **kwargs):
        """Update a question (full update)"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'section': {'type': 'integer'},
                    # 'question_number': {'type': 'integer'},
                    'question_text': {'type': 'string'},
                    'question_type': {
                        'type': 'string',
                        'enum': ['multiple_choice', 'completion', 'matching', 'table']
                    },
                    'question_data': {'type': 'object'},
                    'question_image': {'type': 'string', 'format': 'binary'},
                    # 'correct_answer': {'type': 'object'},
                }
            }
        },
        responses={
            200: ListeningQuestionSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Update a question (partial update)"""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        request={
            'application/json': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'section': {
                            'type': 'integer',
                            'description': 'Section ID'
                        },

                        'question_text': {
                            'type': 'string',
                            'description': 'Savol matni'
                        },
                        'question_type': {
                            'type': 'string',
                            'enum': ['multiple_choice', 'completion', 'matching', 'table'],
                            'description': 'Savol turi'
                        },
                        'question_data': {
                            'type': 'object',
                            'description': 'Savolga oid qo\'shimcha ma\'lumotlar',
                            'example': {"options": ["A) Economy", "B) Technology"]}
                        },
                        'correct_answer': {
                            'type': 'string',
                            'description': 'To\'g\'ri javob'
                        }
                    },
                    'required': ['section', 'question_type']
                },
                'example': [
                    {
                        "section": 1,
                        "question_text": "What is the main topic?",
                        "question_type": "multiple_choice",
                        "question_data": {"options": ["A) Economy", "B) Technology"]},
                    },
                    {
                        "section": 1,
                        "question_text": "Complete: The speaker mentions ___",
                        "question_type": "completion",
                        "question_data": {},
                    }
                ]
            }
        },
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'array',
                        'items': {'$ref': '#/components/schemas/ListeningQuestion'}
                    }
                }
            },
            400: OpenApiTypes.OBJECT
        },
        parameters=[
            OpenApiParameter(
                name='test_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='All questions must belong to sections of this test',
                required=False
            )
        ],
        description="""
        Create multiple listening questions at once.
        Send an array of question objects.
        Optional: Add ?test_id=X to validate all sections belong to test X
        """
    )
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Create multiple questions at once"""
        # 1. List formatini tekshirish
        if not isinstance(request.data, list):
            return Response(
                {"error": "Ma'lumot list formatida bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.data:
            return Response(
                {"error": "Bo'sh list yuborish mumkin emas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Serializer validation
        serializer = self.get_serializer(data=request.data, many=True)

        if not serializer.is_valid():
            return Response(
                {"error": "Validation xatosi", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. test_id parametrini olish
        target_test_id = request.query_params.get('test_id')

        # 4. Section validatsiyasi
        section_ids = {item['section'].id for item in serializer.validated_data}

        if target_test_id:
            # test_id ko'rsatilgan bo'lsa
            try:
                target_test_id = int(target_test_id)
            except ValueError:
                return Response(
                    {"error": "test_id raqam bo'lishi kerak"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            valid_sections = ListeningSection.objects.filter(
                id__in=section_ids,
                test_id=target_test_id
            ).values_list('id', flat=True)

            if set(valid_sections) != section_ids:
                invalid_sections = section_ids - set(valid_sections)
                return Response(
                    {
                        "error": f"Barcha savollar test_id={target_test_id} ga tegishli bo'lishi kerak",
                        "invalid_section_ids": list(invalid_sections)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # test_id ko'rsatilmagan bo'lsa - section mavjudligini tekshirish
            existing_sections = ListeningSection.objects.filter(
                id__in=section_ids
            ).values_list('id', flat=True)

            if set(existing_sections) != section_ids:
                missing_sections = section_ids - set(existing_sections)
                return Response(
                    {
                        "error": "Ba'zi section ID lar mavjud emas",
                        "missing_section_ids": list(missing_sections)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 5. Duplicate question_number tekshirish
        section_question_numbers = {}
        for item in serializer.validated_data:
            section_id = item['section'].id
            question_num = item['question_number']

            if section_id not in section_question_numbers:
                section_question_numbers[section_id] = []

            if question_num in section_question_numbers[section_id]:
                return Response(
                    {
                        "error": f"Section {section_id} da {question_num} raqamli savol takrorlanmoqda",
                        "section_id": section_id,
                        "duplicate_question_number": question_num
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            section_question_numbers[section_id].append(question_num)

        # 6. Mavjud question_number lar bilan konflikt tekshirish
        for section_id, question_numbers in section_question_numbers.items():
            existing_questions = ListeningQuestion.objects.filter(
                section_id=section_id,
                question_number__in=question_numbers
            ).values_list('question_number', flat=True)

            if existing_questions:
                return Response(
                    {
                        "error": f"Section {section_id} da ushbu raqamli savollar allaqachon mavjud",
                        "section_id": section_id,
                        "existing_question_numbers": list(existing_questions)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 7. Saqlash
        try:
            with transaction.atomic():
                questions = serializer.save()
                response_serializer = self.get_serializer(questions, many=True)

                return Response(
                    {
                        "message": f"{len(questions)} ta savol muvaffaqiyatli yaratildi",
                        "data": response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {"error": "Saqlashda xatolik yuz berdi", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


    # @extend_schema(
    #     request={
    #         'application/json': {
    #             'type': 'object',
    #             'properties': {
    #                 'ids': {
    #                     'type': 'array',
    #                     'items': {'type': 'integer'},
    #                     'description': 'O\'chiriladigan savol ID lari'
    #                 }
    #             },
    #             'required': ['ids']
    #         }
    #     },
    #     responses={
    #         200: {
    #             'type': 'object',
    #             'properties': {
    #                 'message': {'type': 'string'},
    #                 'deleted_count': {'type': 'integer'}
    #             }
    #         },
    #         400: OpenApiTypes.OBJECT,
    #         404: OpenApiTypes.OBJECT
    #     },
    #     description='Bir nechta savolni bir vaqtning o\'zida o\'chirish'
    # )
    # @action(detail=False, methods=['post'], url_path='bulk-delete')
    # def bulk_delete(self, request):
    #     """Delete multiple questions at once"""
    #     ids = request.data.get('ids', [])
    #
    #     # Validatsiya
    #     if not isinstance(ids, list):
    #         return Response(
    #             {"error": "'ids' list formatida bo'lishi kerak"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     if not ids:
    #         return Response(
    #             {"error": "'ids' bo'sh bo'lmasligi kerak"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     # Barcha ID lar integer ekanligini tekshirish
    #     if not all(isinstance(id, int) for id in ids):
    #         return Response(
    #             {"error": "Barcha ID lar raqam bo'lishi kerak"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     try:
    #         with transaction.atomic():
    #             # Mavjudligini tekshirish
    #             existing_count = ListeningQuestion.objects.filter(id__in=ids).count()
    #
    #             if existing_count == 0:
    #                 return Response(
    #                     {"error": "Hech qanday savol topilmadi"},
    #                     status=status.HTTP_404_NOT_FOUND
    #                 )
    #
    #             # O'chirish
    #             deleted_count, _ = ListeningQuestion.objects.filter(id__in=ids).delete()
    #
    #             return Response(
    #                 {
    #                     "message": f"{deleted_count} ta savol muvaffaqiyatli o'chirildi",
    #                     "deleted_count": deleted_count
    #                 },
    #                 status=status.HTTP_200_OK
    #             )
    #
    #     except Exception as e:
    #         return Response(
    #             {"error": "O'chirishda xatolik yuz berdi", "details": str(e)},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )


