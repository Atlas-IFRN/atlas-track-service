from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken


class RegrasDeNegocioTests(APITestCase):

    def setUp(self):
        # 1. Token do PROFESSOR
        self.prof_token = AccessToken()
        self.prof_token['user_id'] = '11111111-1111-1111-1111-111111111111'
        self.prof_token['role'] = 'TEACHER'

        # 2. Token do ALUNO
        self.aluno_token = AccessToken()
        self.aluno_token['user_id'] = '22222222-2222-2222-2222-222222222222'
        self.aluno_token['role'] = 'STUDENT'

    def test_01_aluno_nao_pode_criar_trilha(self):
        # Injeção direta do token na requisição (Modo oficial do DRF)
        self.client.force_authenticate(user=None, token=self.aluno_token)

        response = self.client.post(
            '/api/tracks/',
            {
                "creator_id": "11111111-1111-1111-1111-111111111111",
                "title": "Trilha Hacker",
                "description": "Tentando burlar",
                "status": "DRAFT",
            },
            format='json',
        )  # Garantindo que envia como JSON puro

        self.assertEqual(response.status_code, 403)

    def test_02_professor_pode_criar_trilha(self):
        # Injeção do token do professor
        self.client.force_authenticate(user=None, token=self.prof_token)

        response = self.client.post(
            '/api/tracks/',
            {
                "creator_id": "11111111-1111-1111-1111-111111111111",
                "title": "Trilha Oficial",
                "description": "Acesso liberado",
                "status": "DRAFT",
            },
            format='json',
        )

        # O Fofoqueiro: Se der erro de novo, isso vai imprimir o motivo exato no seu terminal!
        if response.status_code != 201:
            print("\n=== MOTIVO DO ERRO DO PROFESSOR ===")
            print(response.data)
            print("===================================\n")

        self.assertEqual(response.status_code, 201)
