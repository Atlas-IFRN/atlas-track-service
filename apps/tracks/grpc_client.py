import grpc
from django.conf import settings

from proto import user_pb2, user_pb2_grpc


def _normalize_grpc_url(grpc_url: str) -> str:
    if grpc_url.startswith("0.0.0.0"):
        _, _, port = grpc_url.rpartition(":")
        return f"host.docker.internal:{port or '50051'}"
    return grpc_url


_GRPC_URL = _normalize_grpc_url(getattr(settings, 'AUTH_GRPC_URL', 'auth-service:50051'))
_channel = grpc.insecure_channel(_GRPC_URL)
_stub = user_pb2_grpc.AuthServiceStub(_channel)


def validate_token(token: str) -> dict | None:
    try:
        response = _stub.ValidateToken(
            user_pb2.ValidateTokenRequest(token=token),
            timeout=3,
        )
        if response.valid:
            return {
                "user_id": response.user_id,
                "role": response.role,
                "email": response.email,
            }
        return None
    except grpc.RpcError:
        return None
