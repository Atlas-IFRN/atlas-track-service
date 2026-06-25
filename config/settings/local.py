"""
Configurações de desenvolvimento local.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

# DATABASES é herdado de base.py:
#   env.db("DATABASE_URL", default="sqlite:///db.sqlite3")
# Com DATABASE_URL definido (ex.: no container), usa PostgreSQL.
# Sem ele, cai no SQLite local para desenvolvimento rápido.
# O schema é selecionado por conexão via a env var PGOPTIONS
# (ex.: PGOPTIONS=-c search_path=tracks,public), definida no docker-compose.
