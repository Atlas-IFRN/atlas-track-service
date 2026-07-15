# Atlas · Tracks Service 🛤️

> Parte do **Projeto Atlas** — plataforma acadêmica desenvolvida para o **IFRN Campus Pau dos Ferros** como Projeto Integrador de Sistemas Distribuídos. O Atlas conecta alunos a trilhas de conhecimento e bolsas, com avaliação automática de código por IA.

Microsserviço responsável pelas **trilhas de aprendizado**: criação e organização de trilhas, módulos e conteúdos, acompanhamento de progresso do aluno e **submissão de desafios** com avaliação automática por IA.

## O que este serviço faz

- **Catálogo de trilhas:** trilhas com categorias, níveis e habilidades (`Skill`), organizadas em módulos e conteúdos.
- **Progresso do aluno:** matrícula em trilhas (`UserTrack`) e progresso por módulo e por conteúdo.
- **Desafios de código:** o aluno envia um repositório GitHub em uma `ChallengeSubmission`; uma **task Celery assíncrona** encaminha o desafio ao **ai-service** (`/analyze`) e persiste o score e o feedback de volta na submissão.
- **Notificações:** dispara eventos de notificação (ex.: resultado da avaliação) via RabbitMQ.
- **Auditoria:** modelo `AuditLog` com registro automático de operações e endpoint de consulta.

## Stack

- Python · Django · Django REST Framework
- PostgreSQL 16 (schema `tracks`) · Redis · RabbitMQ + Celery
- Gunicorn · Docker · drf-spectacular (Swagger)

## Como se encaixa no Atlas

| Repositório | Responsabilidade |
|---|---|
| atlas-auth-service | Identidade: SUAP OAuth2, JWT, perfis de usuário |
| **atlas-track-service** | **Trilhas, módulos, conteúdos, progresso e submissão de desafios** |
| atlas-scholarship-service | Bolsas, candidaturas, banco de talentos e notas |
| atlas-feed-service | Feed institucional: posts, comentários, curtidas e banners |
| atlas-notification-service | Notificações (consumidor central via RabbitMQ) |
| atlas-ai-service | Avaliação de repositórios GitHub por LLM local (Ollama) |
| atlas-frontend | SPA React + TypeScript (aluno e professor) |
| atlas-infra | Docker Compose, Nginx (gateway), Postgres/Redis/RabbitMQ, deploy e backup |
| atlas-observability | Prometheus + Grafana (métricas dos serviços) |

**Autenticação:** o Nginx valida o JWT na borda e injeta `X-User-Id` / `X-User-Role`; o serviço também valida o token localmente (`AtlasJWTAuthentication`, SimpleJWT *stateless*) para ler os claims do usuário. Nenhum serviço acessa o schema do outro — dados cruzados passam pela API HTTP interna.

**Avaliação de desafios:** a submissão roda em um **worker Celery dedicado** (`celery-worker-tracks`, fila `tracks`), mantendo o request do aluno rápido enquanto a análise por IA acontece em segundo plano.

## Domínio (models principais)

`TrackCategory` · `Skill` · `Track` · `Module` · `Content` · `UserTrack` · `UserModuleProgress` · `UserContentProgress` · `ChallengeSubmission` · `AuditLog`

## Principais endpoints (`/api/track/`)

Router DRF: `categories/` · `skills/` · `tracks/` (+ `tracks/search/`) · `modules/` · `contents/` · `user-tracks/` · `module-progress/` · `content-progress/` · `submissions/` · `audit-logs/`. Documentação em `api/track/docs/`.

## Estrutura

```
apps/tracks/   models, views (ViewSets), serializers, services (regra de negócio),
               tasks (Celery), authentication, notifications, tests
config/        settings (base/local/production), urls, celery, asgi, wsgi
```

> Views chamam a camada `services/`; a lógica de negócio não acessa o `request` diretamente.

## Executando localmente

> Orquestrado pelo repositório central: **[Atlas-IFRN/atlas-infra](https://github.com/Atlas-IFRN/atlas-infra)**.

```bash
# 1. Infra compartilhada
git clone https://github.com/Atlas-IFRN/atlas-infra
cd atlas-infra && docker compose -f docker-compose.dev.yml up -d

# 2. Neste repositório
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000

# 3. Worker Celery (avaliação de desafios)
celery -A config worker -l info -Q tracks
```

## Variáveis de ambiente

Baseie seu `.env` no `.env.example`. Principais: `DJANGO_SECRET_KEY` (compartilhada — valida o JWT), `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `AI_SERVICE_URL`, `AI_SERVICE_TIMEOUT`, `AUTH_SERVICE_URL`.

## Observabilidade & Auditoria

- **Métricas:** `/metrics` (django-prometheus), coletado pelo [atlas-observability](https://github.com/Atlas-IFRN/atlas-observability).
- **Auditoria:** `AuditLog` registra operações com `user_id` e timestamp (via signals), consultáveis em `audit-logs/`.

## CI/CD

Workflows de GitHub Actions em `.github/workflows/`.
