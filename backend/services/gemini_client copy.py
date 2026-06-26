"""
Cliente Gemini API para inferência de categoria.

Envia imagem ao modelo gemini-2.0-flash com prompt estruturado.
Devolve a categoria inferida ou "Outros" se o parse/validação falhar.
"""

import json
import logging

import google.generativeai as genai

from config import settings
from models.schemas import CATEGORIAS_VALIDAS

logger = logging.getLogger(__name__)

# Prompt exato conforme secção 7 do agent_rules.md
_PROMPT = """Analisa esta imagem de uma fatura/talão de uma empresa de arquitetura portuguesa.
Responde APENAS com um objeto JSON válido, sem texto adicional, sem markdown:
{"categoria": "<categoria>"}

Categorias possíveis: Material de Escritório, Deslocações e Transportes,
Alimentação e Representação, Telecomunicações, Software e Serviços Digitais,
Equipamento e Ferramentas, Obras e Materiais de Construção, Serviços Externos,
Publicidade e Marketing, Outros.

Se não conseguires determinar a categoria, usa "Outros"."""

# Configurar o SDK uma vez
genai.configure(api_key=settings.GEMINI_API_KEY)


def inferir_categoria(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Envia a imagem ao Gemini e devolve a categoria inferida.

    Args:
        image_bytes: Bytes da imagem (PNG ou JPEG).
        mime_type: MIME type da imagem.

    Returns:
        Uma das categorias válidas definidas no schema,
        ou "Outros" se a inferência falhar.
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            [
                _PROMPT,
                {
                    "mime_type": mime_type,
                    "data": image_bytes,
                },
            ]
        )

        # Extrair texto da resposta
        texto_resposta = response.text.strip()

        # Tentar fazer parse do JSON
        dados = json.loads(texto_resposta)
        categoria = dados.get("categoria", "Outros")

        # Validar que a categoria é uma das permitidas
        if categoria not in CATEGORIAS_VALIDAS:
            logger.warning(
                "Gemini devolveu categoria não reconhecida: '%s'. A usar 'Outros'.",
                categoria,
            )
            return "Outros"

        return categoria

    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        logger.warning(
            "Falha ao fazer parse da resposta do Gemini: %s. A usar 'Outros'.",
            exc,
        )
        return "Outros"

    except Exception as exc:
        logger.error(
            "Erro inesperado na chamada ao Gemini: %s. A usar 'Outros'.",
            exc,
        )
        return "Outros"
