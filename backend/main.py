"""
Entrada FastAPI — registo de routers, middleware de autenticação, CORS.
"""

import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from config import settings
from routes import invoices, reports

# ---------------------------------------------------------------------------
# Configuração de Logging para o Render
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FatureX API",
    description="Sistema de gestão de faturas para empresa de arquitetura.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — permissivo (app mobile é o único cliente)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Autenticação por API Key (header X-API-Key)
# ---------------------------------------------------------------------------
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def _verify_api_key(api_key: str = Depends(_api_key_header)):
    """
    Dependency global que valida a API Key em todas as rotas.
    Responde 401 Unauthorized se a chave estiver ausente ou incorreta.
    """
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — chave API inválida ou ausente.",
        )


# ---------------------------------------------------------------------------
# Registo dos routers com dependency global de autenticação
# ---------------------------------------------------------------------------
app.include_router(invoices.router, dependencies=[Depends(_verify_api_key)])
app.include_router(reports.router, dependencies=[Depends(_verify_api_key)])


@app.get("/", tags=["Health"])
async def health_check():
    """Endpoint de saúde — não requer autenticação."""
    return {"status": "ok", "service": "FatureX API"}


@app.get("/api/test-error", tags=["Debug"])
async def test_error_logging():
    """Endpoint de exemplo para demonstrar a captura e logging de exceções."""
    try:
        # Simulação de erro numa chamada de API de IA ou inserção no Supabase
        raise ValueError("Falha simulada de comunicação com o serviço externo.")
    except Exception:
        # Grava automaticamente a stack trace completa
        logger.exception("Erro ao processar serviço externo (IA/Supabase)")
        raise HTTPException(
            status_code=500,
            detail="Erro interno de simulação de logging."
        )

