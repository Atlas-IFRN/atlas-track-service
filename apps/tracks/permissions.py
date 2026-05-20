from rest_framework import permissions


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Permite GET para todos os autenticados.
    Permite POST, PUT, PATCH, DELETE apenas se a role no token for TEACHER.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        if request.auth:
            return request.auth.get('role') == 'TEACHER'

        return False
