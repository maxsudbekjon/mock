
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dashboard.views import ListeningSectionViewSet, ListeningQuestionViewSet, TestViewSet, ReadingQuestionViewSet, \
    ReadingPassageViewSet, WritingTaskViewSet




router = DefaultRouter()
router.register(r'listening-sections', ListeningSectionViewSet, basename='listening-section')
router.register(r'listening-questions', ListeningQuestionViewSet, basename='listening-question')
router.register(r'Tests', TestViewSet, basename='Ielts-tests')
router.register(r'passages', ReadingPassageViewSet, basename='reading-passage')
router.register(r'questions', ReadingQuestionViewSet, basename='reading-question')
router.register(r'writing-tasks', WritingTaskViewSet, basename='writing-task')



urlpatterns = [
    path('', include(router.urls)),
]