from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['GET'])
def tracks_health_check(request):
    return Response({
        "status": "Serviço de Trilhas operante!",
        "arquitetura": "Enterprise Padrão Ouro concluída com sucesso 🚀"
    })

urlpatterns = [
    path('', tracks_health_check, name='tracks-root'),
]
