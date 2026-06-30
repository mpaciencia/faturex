"""
Configuração central do backend.

Carrega as variáveis de ambiente obrigatórias via pydantic-settings.
Falha imediatamente no arranque se alguma estiver ausente.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    GROQ_API_KEY: str = ""
    NIF_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    ALLOWED_ORIGIN_REGEX: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Instanciação no import — falha de imediato se faltar alguma variável
settings = Settings()
