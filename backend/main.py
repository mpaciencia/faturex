"""
Entrada FastAPI — registo de routers, middleware de autenticação, CORS.
"""

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes import invoices, reports, auth
from routes.deps import get_current_user

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Registo dos routers (públicos e autenticados)
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(invoices.router, dependencies=[Depends(get_current_user)])
app.include_router(reports.router, dependencies=[Depends(get_current_user)])


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

