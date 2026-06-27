"""
Serviço de consulta do NIF.pt para obter o nome da empresa emissora.
"""

import json
import logging
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from config import settings

logger = logging.getLogger(__name__)


def get_nome_emissor(nif: str) -> str | None:
    """
    Consulta o NIF.pt e devolve o nome da empresa associada ao NIF.
    """
    nif_limpo = (nif or "").strip()

    if not nif_limpo.isdigit() or len(nif_limpo) != 9:
        return None

    query_params = {"json": 1, "q": nif_limpo}
    if settings.NIF_API_KEY:
        query_params["key"] = settings.NIF_API_KEY
    query = urlencode(query_params)
    url = f"https://www.nif.pt/?{query}"

    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Erro ao consultar NIF.pt para %s: %s", nif_limpo, exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Erro inesperado ao consultar NIF.pt para %s: %s", nif_limpo, exc)
        return None

    if payload.get("result") != "success":
        return None

    records = payload.get("records")
    if not isinstance(records, dict) or not records:
        return None

    first_record = next(iter(records.values()))
    if not isinstance(first_record, dict):
        return None

    nome = first_record.get("nome") or first_record.get("title") or first_record.get("name")
    return nome if isinstance(nome, str) and nome.strip() else None