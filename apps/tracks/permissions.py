from rest_framework.permissions import SAFE_METHODS, BasePermission

from .grpc_client import validate_token


class IsAuthenticatedViaRPC(BasePermission):
    """
    Liga pro gRPC. Se o token for verdadeiro, deixa passar e salva os dados no request.auth.
    Se for falso/inválido, bloqueia na hora (Retorna 401 Unauthorized).
    """

    def has_permission(self, request, view):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return False

        token_bruto = auth_header.split(" ")[1]
        payload_usuario = validate_token(token_bruto)

        if not payload_usuario:
            return False

        request.auth = payload_usuario
        return True


class IsTeacherOrReadOnly(BasePermission):
    """
    Para rotas onde Aluno só pode olhar (GET), mas só Professor pode criar/editar (POST/PUT/DELETE).
    """

    def has_permission(self, request, view):
        # Se for método de leitura (GET, HEAD, OPTIONS), libera.
        if request.method in SAFE_METHODS:
            return True

        if request.auth:
            return request.auth.get('role') == 'TEACHER'
        return False
