# Tracks Service — Serviço de Trilhas

Um microserviço do ecossistema **Atlas** responsável pelo gerenciamento de trilhas de aprendizado (tracks). Fornece modelos, endpoints e lógica de domínio para criação, atualização e consulta de trilhas e seus conteúdos.

## Tecnologias utilizadas

- **Django** (framework web)
- **PostgreSQL** (banco de dados relacional) — usado no `docker-compose.yml`
- **Docker / Docker Compose** (contêineres e orquestração)
- **django-environ** (gerenciamento de variáveis de ambiente)
- **Django REST Framework** (APIs REST)
- **gRPC** (biblioteca instalada e suporte planejado — implementação futura)
- **psycopg2-binary** (driver PostgreSQL)
- **grpcio / grpcio-tools** (ferramentas gRPC)
- **Pre-commit hooks**: Black, Isort, Autoflake (configurado em `.pre-commit-config.yaml`)

## 1) Setup local (recomendado via Docker) ⚙️

Siga os passos abaixo para rodar o serviço localmente usando Docker Compose.

1. Clone o repositório:

```bash
git clone https://github.com/Atlas-IFRN/atlas-track-service.git
cd Atlas_Track-Services
```

2. Copie o arquivo de exemplo de variáveis de ambiente e edite conforme necessário:

```bash
cp .env.example .env
# (ou no Windows PowerShell)
# Copy-Item .env.example .env
```

3. Suba os containers (build e execução):

```bash
docker compose up --build
```

4. Rode as migrações dentro do container Django (o serviço do Django é chamado `web` no `docker-compose.yml`):

```bash
docker compose exec web python manage.py migrate
```

5. Crie um superusuário (opcional):

```bash
docker compose exec web python manage.py createsuperuser
```

6. (Opcional) Rode a aplicação em background:

```bash
docker compose up -d --build
```

Observação: o `docker-compose.yml` define dois serviços principais: `db` (Postgres) e `web` (Django).

## 2) Estrutura do projeto

Este repositório segue uma arquitetura com separação clara entre configuração do projeto e aplicações Django locais — padrão Enterprise para microserviços:

- `apps/tracks/` — Aplicação local que contém modelos, views, serializers e lógica de domínio específica para trilhas.
- `config/settings/` — Configurações modularizadas por ambiente (base, local, production). Usa `django-environ` para carregar variáveis de ambiente e facilitar deploys/CI.

Essa separação facilita reuso, testes e integração com outros serviços do ecossistema Atlas.

## 3) Documentação da API 📚

### 🔒 Autenticação e Endpoints

A API é protegida e exige o header `Authorization: Bearer <token_jwt>` em todas as requisições. Os tokens são gerenciados pelo serviço de autenticação central do ecossistema Atlas.

```http
Authorization: Bearer <token_jwt>
```

A base das URLs de exemplo é:

```http
http://localhost:8000/api/
```

### Endpoints principais

#### Trilhas (`/api/tracks/`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/tracks/` | Lista todas as trilhas cadastradas |
| `POST` | `/api/tracks/` | Cria uma nova trilha |
| `GET` | `/api/tracks/{id}/` | Retorna detalhes de uma trilha específica |
| `PUT` | `/api/tracks/{id}/` | Atualiza todos os dados da trilha |
| `PATCH` | `/api/tracks/{id}/` | Atualiza dados parciais da trilha |
| `DELETE` | `/api/tracks/{id}/` | Deleta uma trilha |

#### Inscrições de Usuários (`/api/user-tracks/`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/user-tracks/` | Lista as inscrições dos alunos |
| `POST` | `/api/user-tracks/` | Inscreve um aluno em uma trilha |

### Exemplos cURL

#### Criar uma Trilha

```bash
curl -X POST http://localhost:8000/api/tracks/ \
  -H "Authorization: Bearer <token_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "creator_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Introdução a DevOps",
    "description": "Trilha para aprendizado de práticas essenciais de DevOps.",
    "status": "DRAFT"
  }'
```

#### Inscrição de Aluno

```bash
curl -X POST http://localhost:8000/api/user-tracks/ \
  -H "Authorization: Bearer <token_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "track": "987e6543-e21b-12d3-a456-426614174000"
  }'
```

> Nota: a trilha deve estar com `status` igual a `PUBLISHED` para que a inscrição seja aceita.

#### Listagem de Trilhas

```bash
curl -X GET http://localhost:8000/api/tracks/ \
  -H "Authorization: Bearer <token_jwt>"
```

### Regras de Negócio de Segurança

- Inscrições em trilhas com status diferente de `PUBLISHED` são bloqueadas.
- Inscrições duplicadas para o mesmo usuário na mesma trilha são impedidas pela lógica de domínio.
- Todas as requisições dependem do `Authorization: Bearer <token_jwt>` e serão rejeitadas se o token estiver ausente ou inválido.

## 4) Qualidade de código (pre-commit) ✅

Recomendamos usar `pre-commit` para garantir formatação e limpeza automáticas antes dos commits (Black, Isort, Autoflake, entre outros hooks configurados).

Instalação e ativação local:

```bash
pip install pre-commit
pre-commit install
```

Executar manualmente em todos os arquivos:

```bash
pre-commit run --all-files
```

O arquivo `.pre-commit-config.yaml` já inclui hooks para `black`, `isort`, `autoflake` e verificações básicas de YAML/JSON e debug-statements.

## 5) Comandos úteis (rotina de desenvolvimento) 🧰

```bash
# Subir containers (modo interativo)
docker compose up --build

# Subir em background
docker compose up -d --build

# Parar e remover containers
docker compose down

# Acessar shell do container web
docker compose exec web /bin/bash

# Rodar migrações
docker compose exec web python manage.py migrate

# Criar migrations (local app)
docker compose exec web python manage.py makemigrations

# Criar superusuário
docker compose exec web python manage.py createsuperuser

# Rodar testes
docker compose exec web python manage.py test

# Executar checks do Django (pré-commit também chama isso)
docker compose exec web python manage.py check
```

---

![DER Inicial](docs/der-inicial-tracks.png)
