from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsTeacherOrReadOnly(BasePermission):
    """
    Para rotas onde Aluno só pode olhar (GET), mas só Professor pode criar/editar (POST/PUT/DELETE).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("Token de autenticação não fornecido.")
        if getattr(user, "role", None) != "TEACHER":
            raise PermissionDenied("Apenas usuários com perfil de professor podem modificar este recurso.")
        return True
