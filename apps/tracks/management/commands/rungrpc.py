import grpc
from concurrent import futures
from django.core.management.base import BaseCommand
from apps.tracks.grpc import tracks_pb2_grpc
from apps.tracks.grpc.services import TracksService

class Command(BaseCommand):
    help = 'Inicia o servidor gRPC do Tracks Service na porta 50051'

    def handle(self, *args, **options):
        # Cria um servidor capaz de atender 10 requisições simultâneas
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Conecta a nossa lógica (TracksService) ao servidor
        tracks_pb2_grpc.add_TracksServiceServicer_to_server(TracksService(), server)
        
        # Define a porta padrão do gRPC
        server.add_insecure_port('[::]:50051')
        
        self.stdout.write(self.style.SUCCESS('🟢 Servidor gRPC iniciado e escutando na porta 50051...'))
        server.start()
        
        # Mantém o servidor rodando infinitamente
        server.wait_for_termination()