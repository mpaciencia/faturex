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


def insert_fatura(data: dict, user_id: str) -> dict:
    """
    Insere um registo na tabela 'faturas'.

    Args:
        data: Dicionário com os campos da fatura (correspondentes às colunas da tabela).
        user_id: ID do utilizador dono da fatura.

    Returns:
        Dicionário com o registo inserido (inclui 'id' gerado pelo Supabase).

    Raises:
        Exception: Se a inserção falhar no Supabase.
    """
    try:
        logger.info("A tentar inserir fatura no Supabase (ATCUD: %s, User: %s)", data.get("atcud"), user_id)
        data["user_id"] = user_id
        response = _client.table(_TABLE).insert(data).execute()

        if not response.data:
            raise Exception("Falha ao inserir fatura no Supabase: resposta vazia.")

        logger.info("Fatura inserida com sucesso no Supabase (ATCUD: %s)", data.get("atcud"))
        return response.data[0]
    except Exception:
        logger.exception("Erro ao inserir fatura no Supabase (ATCUD: %s)", data.get("atcud"))
        raise


def fatura_exists(atcud: str, user_id: str) -> bool:
    """
    Verifica se já existe uma fatura com o ATCUD fornecido para o utilizador.

    Args:
        atcud: Código único AT da fatura.
        user_id: ID do utilizador.

    Returns:
        True se a fatura já existir para este utilizador, False caso contrário.
    """
    try:
        logger.info("A verificar se fatura já existe no Supabase (ATCUD: %s, User: %s)", atcud, user_id)
        response = (
            _client.table(_TABLE)
            .select("id")
            .eq("atcud", atcud)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        exists = len(response.data) > 0
        logger.info("Verificação de existência de fatura concluída (ATCUD: %s, Existe: %s)", atcud, exists)
        return exists
    except Exception:
        logger.exception("Erro ao verificar existência da fatura no Supabase (ATCUD: %s)", atcud)
        raise


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
    try:
        logger.info("A iniciar upload de documento para Supabase Storage (path: %s, tipo: %s)", path, content_type)
        _client.storage.from_(_BUCKET).upload(
            path=path,
            file=content,
            file_options={"content-type": content_type},
        )

        # Obter URL pública do ficheiro
        url_response = _client.storage.from_(_BUCKET).get_public_url(path)
        logger.info("Upload de documento concluído com sucesso (URL: %s)", url_response)
        return url_response
    except Exception:
        logger.exception("Erro no upload do documento para o Supabase Storage (path: %s)", path)
        raise


def download_documento(path: str) -> bytes:
    """
    Faz download de um ficheiro do Supabase Storage.

    Args:
        path: Caminho relativo dentro do bucket.

    Returns:
        Bytes do ficheiro descarregado.
    """
    try:
        logger.info("A iniciar download de documento do Supabase Storage (path: %s)", path)
        response = _client.storage.from_(_BUCKET).download(path)

        data_bytes = None
        if isinstance(response, bytes):
            data_bytes = response
        elif hasattr(response, "data") and isinstance(response.data, (bytes, bytearray)):
            data_bytes = bytes(response.data)
        elif hasattr(response, "content") and isinstance(response.content, (bytes, bytearray)):
            data_bytes = bytes(response.content)

        if data_bytes is not None:
            logger.info("Download concluído com sucesso (%d bytes)", len(data_bytes))
            return data_bytes

        raise Exception(f"Falha ao descarregar documento do Supabase: {path}")
    except Exception:
        logger.exception("Erro ao transferir documento do Supabase Storage (path: %s)", path)
        raise


def storage_path_from_public_url(url: str) -> str:
    """
    Extrai o path do objeto a partir de uma URL pública do Supabase Storage.
    """
    parsed = urlparse(url)
    marker = "/object/public/"

    if marker not in parsed.path:
        raise ValueError(f"URL de documento inválida: {url}")

    return parsed.path.split(marker, 1)[1].split("/", 1)[1]


def get_faturas_by_period(data_inicio: str, data_fim: str, user_id: str) -> list:
    """
    Consulta faturas filtradas por intervalo de data_fatura (inclusive) e utilizador.

    Args:
        data_inicio: Data de início no formato 'YYYY-MM-DD'.
        data_fim: Data de fim no formato 'YYYY-MM-DD'.
        user_id: ID do utilizador.

    Returns:
        Lista de dicionários com os registos das faturas.
    """
    try:
        logger.info("A consultar faturas no Supabase no intervalo: %s a %s, User: %s", data_inicio, data_fim, user_id)
        response = (
            _client.table(_TABLE)
            .select("*")
            .gte("data_fatura", data_inicio)
            .lte("data_fatura", data_fim)
            .eq("user_id", user_id)
            .order("data_fatura")
            .execute()
        )
        logger.info("Consulta ao Supabase concluída. Encontradas %d faturas", len(response.data))
        return response.data
    except Exception:
        logger.exception("Erro ao obter faturas por período do Supabase (%s a %s)", data_inicio, data_fim)
        raise


def authenticate_user(email: str, password: str):
    """
    Autentica um utilizador com email e password no Supabase Auth.
    """
    try:
        logger.info("A tentar autenticar utilizador: %s", email)
        response = _client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response
    except Exception:
        logger.exception("Erro ao autenticar utilizador: %s", email)
        raise


def get_user_from_token(token: str):
    """
    Obtém o utilizador correspondente ao JWT fornecido.
    Valida o token com o servidor do Supabase.
    """
    try:
        response = _client.auth.get_user(token)
        return response.user
    except Exception:
        logger.exception("Erro ao validar token JWT")
        raise
