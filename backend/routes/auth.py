"""
Rotas de autenticação — POST /api/auth/login.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str
    user_id: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    logger.info("Recebida requisição de login para o utilizador: %s", payload.email)
    try:
        response = supabase_client.authenticate_user(payload.email, payload.password)
        session = response.session
        user = response.user

        if not session or not user:
            raise HTTPException(
                status_code=401,
                detail="Credenciais inválidas ou erro ao autenticar.",
            )

        logger.info("Login efetuado com sucesso para o utilizador: %s", payload.email)
        return LoginResponse(
            access_token=session.access_token,
            user_email=user.email,
            user_id=user.id,
        )
    except Exception as exc:
        logger.error("Falha na autenticação do utilizador %s: %s", payload.email, exc)
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas ou erro ao autenticar.",
        )
