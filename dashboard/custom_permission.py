from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions


# class IsTeacherOrAdmin(IsAuthenticated):
#     """Teacher yoki Admin permission"""
#
#     def has_permission(self, request, view):
#         return (
#                 super().has_permission(request, view) and
#                 (request.user.is_teacher or request.user.is_admin_user)
#         )


class IsTeacherOrAdminOrReadOnly(permissions.BasePermission):
    """
    Admin/Teacher: CRUD qila oladi
    Oddiy user: Faqat o'qiy oladi (GET)
    """

    def has_permission(self, request, view):
        # GET, HEAD, OPTIONS - hamma uchun ruxsat
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # POST, PUT, PATCH, DELETE - faqat Admin/Teacher
        return (
                request.user.is_authenticated and
                (request.user.is_staff or request.user.role in ['admin', 'teacher'])
        )
