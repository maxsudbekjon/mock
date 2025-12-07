from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenRefreshView


@extend_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)