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
# CORS
# ---------------------------------------------------------------------------
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
origin_regex = settings.ALLOWED_ORIGIN_REGEX if settings.ALLOWED_ORIGIN_REGEX else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
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


