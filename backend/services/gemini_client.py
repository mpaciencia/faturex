"""
Cliente Groq API para inferência de categoria.

Envia imagem ao modelo llama-3.2-11b-vision-instruct com prompt estruturado.
Devolve a categoria inferida ou "Outros" se o parse/validação falhar.
"""

import base64
import json
import logging

from groq import Groq

from config import settings
from models.schemas import CATEGORIAS_VALIDAS

logger = logging.getLogger(__name__)

_PROMPT = """Analisa esta imagem de uma fatura/talão de uma empresa de arquitetura portuguesa.
Responde APENAS com um objeto JSON válido, sem texto adicional, sem markdown:
{"categoria": "<categoria>"}

Categorias possíveis: Material de Escritório, Deslocações e Transportes,
Alimentação e Representação, Telecomunicações, Software e Serviços Digitais,
Equipamento e Ferramentas, Obras e Materiais de Construção, Serviços Externos,
Publicidade e Marketing, Outros.

Se não conseguires determinar a categoria, usa "Outros"."""

_client = Groq(api_key=settings.GROQ_API_KEY)


def inferir_categoria(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Envia a imagem ao Groq e devolve a categoria inferida.

    Args:
        image_bytes: Bytes da imagem (PNG ou JPEG).
        mime_type: MIME type da imagem.

    Returns:
        Uma das categorias válidas definidas no schema,
        ou "Outros" se a inferência falhar.
    """
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = _client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
            max_tokens=64,
            temperature=0,
        )

        texto_resposta = response.choices[0].message.content.strip()

        dados = json.loads(texto_resposta)
        categoria = dados.get("categoria", "Outros")

        if categoria not in CATEGORIAS_VALIDAS:
            logger.warning(
                "Groq devolveu categoria não reconhecida: '%s'. A usar 'Outros'.",
                categoria,
            )
            return "Outros"

        return categoria

    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        logger.warning(
            "Falha ao fazer parse da resposta do Groq: %s. A usar 'Outros'.",
            exc,
        )
        return "Outros"

    except Exception as exc:
        logger.error(
            "Erro inesperado na chamada ao Groq: %s. A usar 'Outros'.",
            exc,
        )
        return "Outros"