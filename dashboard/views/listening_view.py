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


@extend_schema(tags=['Listening question'])
class ListeningQuestionViewSet(viewsets.ModelViewSet):
    """
    Savollar bilan ishlash.
    Features:
    - Test ID bo'yicha filterlash (GET /questions/?test_id=1)
    - Section ID bo'yicha filterlash (GET /questions/?section_id=5)
    - Bulk Create (Tranzaksiya bilan)
    """
    # select_related('section__test') orqali DB ga bitta so'rov bilan Test ma'lumotlarini ham olamiz
    queryset = ListeningQuestion.objects.all().select_related('section', 'section__test')
    serializer_class = ListeningQuestionSerializer
    permission_classes = [IsTeacherOrAdminOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    filterset_fields = ['section', 'section__test']
    ordering_fields = ['question_number']




    @extend_schema(
        summary="Ko'p savollarni bittada yaratish (Bulk Create)",
        description="""
        JSON Array ko'rinishida savollarni yuboring. 
        Mantiqiy bog'liqlik: Savol Sectionga ulanadi, Section esa Testga. 
        Shuning uchun Section ID to'g'ri bo'lsa, Testga avtomatik bog'lanadi.
        """,
        request=ListeningQuestionSerializer(many=True),
        responses={201: ListeningQuestionSerializer(many=True)}
    )
    


    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)



        target_test_id = request.query_params.get('test_id')
        if target_test_id:
            section_ids = {item['section'].id for item in serializer.validated_data}

            valid_sections = ListeningSection.objects.filter(
                id__in=section_ids,
                test_id=target_test_id
            ).count()

            if valid_sections != len(section_ids):
                return Response(
                    {"error": "Barcha savollar ko'rsatilgan Test ID ga tegishli sectionlarga biriktirilishi shart!"},
                    status=status.HTTP_400_BAD_REQUEST
                )


        try:
            with transaction.atomic():
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Saqlashda xatolik: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )