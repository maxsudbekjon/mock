from django.urls import path, include
from app.views import RegisterView, LoginView, ProfileView,  \
    ListeningAnswerSubmitView, \
    ListeningBulkAnswerSubmitView, StudentListeningResultView, \
    StudentListeningStatusView
from rest_framework.routers import DefaultRouter

from app.views import TestAttemptViewSet

router = DefaultRouter()
router.register('attempts', TestAttemptViewSet, basename='attempt')


urlpatterns = [

    path('', include(router.urls)),

    # user
    path('user/register/', RegisterView.as_view(), name='user_register'),
    path('user/login/', LoginView.as_view(), name='user_login'),
    path('user/profile/', ProfileView.as_view(), name='user_profile'),

    # Student endpoints
    # path('tests/<int:test_id>/listening/',
    #      ListeningSectionListView.as_view(),
    #      name='listening-sections'),

    path('listening/answer/',
         ListeningAnswerSubmitView.as_view(),
         name='listening-answer-submit'),

    path('listening/bulk-answer/',
         ListeningBulkAnswerSubmitView.as_view(),
         name='listening-bulk-answer'),

    path('listening/my-result/',
         StudentListeningResultView.as_view(),
         name='listening-my-result'),

    path('listening/status/',
         StudentListeningStatusView.as_view(),
         name='listening-status'),


]