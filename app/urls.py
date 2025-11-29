from django.urls import path
from .views import RegisterView, LoginView, ProfileView



urlpatterns = [

    # user
    path('user/register/', RegisterView.as_view(), name='user_register'),
    path('user/login/', LoginView.as_view(), name='user_login'),
    path('user/profile/', ProfileView.as_view(), name='user_profile'),

]