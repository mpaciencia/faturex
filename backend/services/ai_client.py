"""
Cliente de IA para inferência de categoria.

Envia a imagem ao modelo de linguagem configurado (atualmente Groq/Llama) com prompt estruturado.
Devolve a categoria inferida ou "Outros" se o parse/validação falhar.
"""

import base64
import json
import logging
import re

from groq import Groq

from config import settings
from models.schemas import CATEGORIAS_VALIDAS

logger = logging.getLogger(__name__)

_PROMPT = """Classifica esta fatura/talão numa ÚNICA categoria. Responde SÓ com JSON, nada mais.
{"categoria": "<categoria>"}

CATEGORIAS E EXEMPLOS:
- Alimentação e Representação → cafés, restaurantes, supermercados, pastelarias, padarias, Nespresso, snacks, água, refeições
- Deslocações e Transportes → combustível, portagens, estacionamento, táxis, Uber, Bolt, bilhetes de transporte, Via Verde
- Material de Escritório → papel, canetas, tinteiros, impressão, encadernação, livrarias, papelarias, cartuchos
- Telecomunicações → telemóvel, internet, NOS, MEO, Vodafone, telefone fixo
- Software e Serviços Digitais → licenças, subscrituras, domínios, hosting, Adobe, Microsoft, Google, apps
- Equipamento e Ferramentas → computadores, monitores, ferramentas, máquinas, hardware, eletrodomésticos, eletrónica
- Obras e Materiais de Construção → cimento, tijolos, tintas, madeira, ferragens, materiais de construção, Leroy Merlin
- Serviços Externos → seguros, contabilidade, consultoria, advogados, limpeza, manutenção, serviços profissionais
- Publicidade e Marketing → impressão gráfica, flyers, publicidade online, Google Ads, redes sociais, brindes
- Outros → APENAS se nenhuma categoria acima se aplicar

REGRA: decide pela atividade principal do emissor ou pelo produto comprado. Não hesites.
/no_think"""

_client = Groq(api_key=settings.GROQ_API_KEY)


def inferir_categoria(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Envia a imagem ao serviço de IA e devolve a categoria inferida.

    Args:
        image_bytes: Bytes da imagem (PNG ou JPEG).
        mime_type: MIME type da imagem.

    Returns:
        Uma das categorias válidas definidas no schema,
        ou "Outros" se a inferência falhar.
    """
    try:
        logger.info("Iniciando inferência de categoria via IA (tipo: %s)", mime_type)
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = _client.chat.completions.create(
            model="qwen/qwen3.6-27b",
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
            max_tokens=1024,
            temperature=0.6,
        )

        raw_content = response.choices[0].message.content
        logger.debug("Resposta bruta da IA: %r", raw_content)

        if not raw_content or not raw_content.strip():
            logger.warning("Serviço de IA devolveu resposta vazia. A usar 'Outros'.")
            return "Outros"

        texto_resposta = raw_content.strip()

        # Remover thinking tags (completas ou incompletas por truncagem)
        if "<think>" in texto_resposta:
            # Tag completa: <think>...</think>
            texto_resposta = re.sub(r"<think>.*?</think>", "", texto_resposta, flags=re.DOTALL).strip()
            # Tag incompleta (cortada pelo max_tokens): <think>... sem </think>
            if "<think>" in texto_resposta:
                texto_resposta = re.sub(r"<think>.*", "", texto_resposta, flags=re.DOTALL).strip()

        # Tentar extrair JSON mesmo se vier com markdown (```json ... ```)
        if "```" in texto_resposta:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto_resposta, re.DOTALL)
            if json_match:
                texto_resposta = json_match.group(1)

        # Último recurso: procurar qualquer objeto JSON na resposta
        if not texto_resposta.startswith("{"):
            json_match = re.search(r"(\{[^}]*\})", texto_resposta)
            if json_match:
                texto_resposta = json_match.group(1)

        dados = json.loads(texto_resposta)
        categoria = dados.get("categoria", "Outros")

        if categoria not in CATEGORIAS_VALIDAS:
            logger.warning(
                "Serviço de IA devolveu categoria não reconhecida: '%s'. A usar 'Outros'.",
                categoria,
            )
            return "Outros"

        return categoria

    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        logger.warning(
            "Falha ao fazer parse da resposta do serviço de IA: %s. A usar 'Outros'.",
            exc,
        )
        return "Outros"

    except Exception:
        logger.exception("Erro inesperado na chamada ao serviço de IA. A usar 'Outros'.")
        return "Outros"

