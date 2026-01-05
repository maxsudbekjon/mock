from django.urls import path, include
from .views import CustomTokenRefreshView
from app.views import RegisterView, LoginView, ProfileView
from rest_framework.routers import DefaultRouter


from .views import (
    ListeningSubmissionViewSet,
    ReadingSubmissionViewSet,
    WritingSubmissionViewSet,
    TestAttemptViewSet
)

router = DefaultRouter()
router.register(r'listening', ListeningSubmissionViewSet, basename='listening')
router.register(r'reading', ReadingSubmissionViewSet, basename='reading')
router.register(r'writing', WritingSubmissionViewSet, basename='writing')
router.register(r'attempts', TestAttemptViewSet, basename='attempts')



urlpatterns = [

    # path('', include(router.urls)),

    # user auth
    path('user/register/', RegisterView.as_view(), name='user_register'),
    path('user/login/', LoginView.as_view(), name='user_login'),
    path('user/profile/', ProfileView.as_view(), name='user_profile'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    # path('teacher/login/', TeacherLoginAPIView.as_view(), name='teacher-login'),

    #answer submit
    path('submissions/', include(router.urls)),





]