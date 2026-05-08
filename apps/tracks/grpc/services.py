from . import tracks_pb2, tracks_pb2_grpc


# Herdamos a classe base gerada automaticamente pelo compilador
class TracksService(tracks_pb2_grpc.TracksServiceServicer):

    # Este método tem exatamente o mesmo nome que definimos lá no .proto
    def GetTrackInfo(self, request, context):
        print(f"🚀 [gRPC] Recebida requisição para a trilha ID: {request.track_id}")

        # Aqui no futuro faremos a busca real no banco usando o models.py
        # Por enquanto, retornamos um dado estático no formato exato do TrackResponse
        return tracks_pb2.TrackResponse(
            id=request.track_id,
            title="Trilha de Arquitetura de Software",
            description="Aprenda a construir sistemas escaláveis e resilientes.",
            status="ACTIVE",
        )
