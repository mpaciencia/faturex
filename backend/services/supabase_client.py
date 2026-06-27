"""
Wrapper de acesso ao Supabase (DB + Storage).

Expõe funções para inserir faturas, verificar duplicados,
fazer upload de documentos e consultar faturas por período.
"""

import logging
from urllib.parse import urlparse

from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)

_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

_TABLE = "faturas"
_BUCKET = "documentos"


def insert_fatura(data: dict) -> dict:
    """
    Insere um registo na tabela 'faturas'.

    Args:
        data: Dicionário com os campos da fatura (correspondentes às colunas da tabela).

    Returns:
        Dicionário com o registo inserido (inclui 'id' gerado pelo Supabase).

    Raises:
        Exception: Se a inserção falhar no Supabase.
    """
    response = _client.table(_TABLE).insert(data).execute()

    if not response.data:
        raise Exception("Falha ao inserir fatura no Supabase: resposta vazia.")

    return response.data[0]


def fatura_exists(atcud: str) -> bool:
    """
    Verifica se já existe uma fatura com o ATCUD fornecido.

    Args:
        atcud: Código único AT da fatura.

    Returns:
        True se a fatura já existir, False caso contrário.
    """
    response = (
        _client.table(_TABLE)
        .select("id")
        .eq("atcud", atcud)
        .limit(1)
        .execute()
    )
    return len(response.data) > 0


def upload_documento(path: str, content: bytes, content_type: str) -> str:
    """
    Faz upload de um ficheiro para o Supabase Storage.

    Args:
        path: Caminho relativo dentro do bucket (ex: 'email/2025/06/ABCD1234-1.pdf').
        content: Bytes do ficheiro.
        content_type: MIME type do ficheiro (ex: 'application/pdf', 'image/jpeg').

    Returns:
        URL pública do ficheiro no Storage.

    Raises:
        Exception: Se o upload falhar.
    """
    _client.storage.from_(_BUCKET).upload(
        path=path,
        file=content,
        file_options={"content-type": content_type},
    )

    # Obter URL pública do ficheiro
    url_response = _client.storage.from_(_BUCKET).get_public_url(path)
    return url_response


def download_documento(path: str) -> bytes:
    """
    Faz download de um ficheiro do Supabase Storage.

    Args:
        path: Caminho relativo dentro do bucket.

    Returns:
        Bytes do ficheiro descarregado.
    """
    response = _client.storage.from_(_BUCKET).download(path)

    if isinstance(response, bytes):
        return response

    if hasattr(response, "data") and isinstance(response.data, (bytes, bytearray)):
        return bytes(response.data)

    if hasattr(response, "content") and isinstance(response.content, (bytes, bytearray)):
        return bytes(response.content)

    raise Exception(f"Falha ao descarregar documento do Supabase: {path}")


def storage_path_from_public_url(url: str) -> str:
    """
    Extrai o path do objeto a partir de uma URL pública do Supabase Storage.
    """
    parsed = urlparse(url)
    marker = "/object/public/"

    if marker not in parsed.path:
        raise ValueError(f"URL de documento inválida: {url}")

    return parsed.path.split(marker, 1)[1].split("/", 1)[1]


def get_faturas_by_period(data_inicio: str, data_fim: str) -> list:
    """
    Consulta faturas filtradas por intervalo de data_fatura (inclusive).

    Args:
        data_inicio: Data de início no formato 'YYYY-MM-DD'.
        data_fim: Data de fim no formato 'YYYY-MM-DD'.

    Returns:
        Lista de dicionários com os registos das faturas.
    """
    response = (
        _client.table(_TABLE)
        .select("*")
        .gte("data_fatura", data_inicio)
        .lte("data_fatura", data_fim)
        .order("data_fatura")
        .execute()
    )
    return response.data
