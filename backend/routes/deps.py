"""
Dependências de rota para FastAPI (ex: autenticação).
"""

import logging
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.supabase_client import get_user_from_token

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """
    Dependency global/local que valida o token JWT obtido no cabeçalho Authorization (Bearer).
    Retorna o objeto de utilizador autenticado se válido.
    """
    if not credentials:
        logger.warning("Tentativa de acesso sem cabeçalho Authorization.")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — Token de acesso ausente.",
        )

    token = credentials.credentials
    try:
        user = get_user_from_token(token)
        if not user:
            logger.warning("Token JWT inválido ou utilizador correspondente inexistente.")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized — Token inválido ou utilizador não encontrado.",
              )
        return user
    except Exception as exc:
        logger.error("Erro na validação do token JWT: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — Token inválido ou expirado.",
        )
