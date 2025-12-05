from rest_framework.permissions import IsAuthenticated


class IsTeacherOrAdmin(IsAuthenticated):
    """Teacher yoki Admin permission"""

    def has_permission(self, request, view):
        return (
                super().has_permission(request, view) and
                (request.user.is_teacher or request.user.is_admin_user)
        )