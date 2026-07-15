"""Autenticação stateless pelo JWT emitido pelo Auth Service."""

from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.models import TokenUser

from .audit import set_current_actor_id


class AtlasTokenUser(TokenUser):
    @property
    def user_id(self):
        return str(self.id)

    @property
    def role(self):
        return self.token.get('role', '')

    @property
    def email(self):
        return self.token.get('email', '')

    @property
    def ira(self):
        return self.token.get('ira')

    @property
    def period(self):
        return self.token.get('period')

    @property
    def is_staff(self):
        return bool(self.token.get('is_staff', False))


class AtlasJWTAuthentication(JWTStatelessUserAuthentication):
    """Valida o JWT e disponibiliza o usuário atual aos signals de auditoria."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            set_current_actor_id(result[0].id)
        return result
