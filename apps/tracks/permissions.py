from rest_framework.permissions import SAFE_METHODS, BasePermission

from .grpc_client import validate_token


class IsAuthenticatedViaRPC(BasePermission):
    """
    Liga pro gRPC. Se o token for verdadeiro, deixa passar e salva os dados em request.auth.
    Se for falso/inválido, bloqueia na hora (Retorna 401 Unauthorized).
    """

    def has_permission(self, request, view):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header.split(" ")[1]
        payload = validate_token(token)

        if not payload:
            return False

        request.auth = payload
        return True


class IsTeacherOrReadOnly(BasePermission):
    """
    Para rotas onde Aluno só pode olhar (GET), mas só Professor pode criar/editar (POST/PUT/DELETE).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if request.auth:
            return request.auth.get('role') == 'TEACHER'
        return False
