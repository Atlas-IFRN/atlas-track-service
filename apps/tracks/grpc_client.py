import grpc
from django.conf import settings

from proto import user_pb2, user_pb2_grpc


def _normalize_grpc_url(grpc_url: str) -> str:
    if grpc_url.startswith("0.0.0.0"):
        _, _, port = grpc_url.rpartition(":")
        return f"host.docker.internal:{port or '50051'}"
    return grpc_url


def validate_token(token: str):
    """
    Pega o token bruto, liga para o auth-service via gRPC e pergunta se é válido.
    Retorna os dados do usuário se for válido, ou None se for falso/expirado.
    """
    # 1. Pega a URL do serviço auth lá do seu settings/env (ex: localhost:50051)
    grpc_url = _normalize_grpc_url(getattr(settings, 'AUTH_GRPC_URL', 'localhost:50051'))

    # 2. Abre o canal de comunicação (tira o telefone do gancho)
    try:
        with grpc.insecure_channel(grpc_url) as channel:
            # 3. Prepara para falar a mesma língua do contrato
            stub = user_pb2_grpc.AuthServiceStub(channel)

            # 4. Faz a pergunta enviando o token
            resposta = stub.ValidateToken(user_pb2.ValidateTokenRequest(token=token), timeout=3)

            if resposta.valid:
                return {
                    "user_id": resposta.user_id,
                    "role": resposta.role,
                    "email": resposta.email,
                }
            return None

    except grpc.RpcError as e:
        print(f"Erro na comunicação gRPC com o Auth Service: {e}")
        return None
