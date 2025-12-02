
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dashboard.views import ListeningSectionViewSet, ListeningQuestionViewSet, TestViewSet



router = DefaultRouter()
router.register(r'listening-sections', ListeningSectionViewSet, basename='listening-section')
router.register(r'listening-questions', ListeningQuestionViewSet, basename='listening-question')
router.register(r'Tests', TestViewSet, basename='Ielts-tests')

urlpatterns = [
    path('', include(router.urls)),
]