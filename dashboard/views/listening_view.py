from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from app.models import ListeningSection, ListeningQuestion
from dashboard.serializers import ListeningSectionSerializer, ListeningQuestionSerializer





@extend_schema(tags=["Listening_section"])
class ListeningSectionViewSet(viewsets.ModelViewSet):
    """
    Listening Sectionlari bilan ishlash:
    - Audio yuklash (multipart/form-data)
    - Test bo'yicha filterlash
    """
    queryset = ListeningSection.objects.all()
    serializer_class = ListeningSectionSerializer
    permission_classes = [IsAuthenticated]  # Yoki IsTeacherOrAdmin
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]  # Fayl yuklash uchun shart

    def get_queryset(self):
        """Test ID bo'yicha filterlash imkonini beradi: /sections/?test_id=1"""
        queryset = super().get_queryset()
        test_id = self.request.query_params.get('test_id')
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        return queryset

    @extend_schema(
        summary="Yangi Section yaratish (Audio bilan)",
        description="Audio fayl va duration majburiy.",
        request=ListeningSectionSerializer
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


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
    permission_classes = [IsAuthenticated]

    # Filterlash uchun eng qulay usul (qo'lda yozgandan ko'ra)
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    # Filterlash mumkin bo'lgan maydonlar:
    # 'section': section ID bo'yicha
    # 'section__test': section ichidagi test ID bo'yicha (BU SIZ SO'RAGAN NARSANGIZ)
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

        # -----------------------------------------------------------
        # QO'SHIMCHA TEKSHIRUV (TESTGA BOG'LIQLIKNI NAZORAT QILISH)
        # -----------------------------------------------------------
        # Agar URLda ?test_id=5 deb yuborilsa, biz barcha savollar
        # aynan shu testga tegishli sectionlarga qo'shilayotganini tekshirishimiz mumkin.

        target_test_id = request.query_params.get('test_id')
        if target_test_id:
            # Kelayotgan ma'lumotlardan section ID larni yig'ib olamiz
            section_ids = {item['section'].id for item in serializer.validated_data}

            # Shu sectionlar rostan ham target_test_id ga tegishlimi tekshiramiz
            valid_sections = ListeningSection.objects.filter(
                id__in=section_ids,
                test_id=target_test_id
            ).count()

            if valid_sections != len(section_ids):
                return Response(
                    {"error": "Barcha savollar ko'rsatilgan Test ID ga tegishli sectionlarga biriktirilishi shart!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # -----------------------------------------------------------

        try:
            with transaction.atomic():
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Saqlashda xatolik: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )