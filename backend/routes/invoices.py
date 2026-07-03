"""
Rotas de faturas — POST /api/faturas/mobile, /email e /pdf.

Os routers apenas orquestram serviços. A lógica partilhada de processamento
de PDFs está centralizada em _process_pdf_and_save.
"""

import asyncio
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from .deps import get_current_user

from models.schemas import FaturaCreateResponse, QRDataPayload, TIPOS_VALIDOS
from services import ai_client, supabase_client
from services.nif_service import get_nome_emissor
from services.pdf_processor import PDFProcessingError, extract_qr_from_pdf
from services.qr_parser import QRParseError, parse_qr_string

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/faturas", tags=["Faturas"])

# Limite de tamanho de upload (20 MB)
MAX_UPLOAD_SIZE = 20 * 1024 * 1024


def _build_storage_path(origem: str, data_fatura: str, atcud: str, ext: str, user_id: str) -> str:
    """
    Constrói o path no Storage: {user_id}/{origem}/{ano}/{mes}/{atcud}.{ext}

    Args:
        origem: 'Mobile' ou 'Email'.
        data_fatura: Data no formato 'YYYY-MM-DD'.
        atcud: Código único AT.
        ext: Extensão do ficheiro (sem ponto).
        user_id: ID do utilizador dono do ficheiro.
    """
    if not re.match(r"^[A-Za-z0-9\-]+$", atcud):
        raise HTTPException(
            status_code=400,
            detail="Código ATCUD inválido para armazenamento (path traversal detectado)."
        )
    ano = data_fatura[:4]
    mes = data_fatura[5:7]
    return f"{user_id}/{origem}/{ano}/{mes}/{atcud}.{ext}"


def _validate_upload_size(file_bytes: bytes) -> None:
    """Valida que o ficheiro não excede o tamanho máximo permitido."""
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Ficheiro excede o tamanho máximo permitido ({MAX_UPLOAD_SIZE // (1024 * 1024)} MB).",
        )


async def _process_pdf_and_save(
    pdf_bytes: bytes,
    user_id: str,
    origem: str,
    tipo: str = "Despesa",
    observacoes: str | None = None,
) -> FaturaCreateResponse:
    """
    Lógica partilhada para processar um PDF de fatura e gravar no Supabase.

    Sequência: extrair QR → parse → verificar duplicado → upload Storage
    → inferir categoria via AI → inserir na DB.

    Args:
        pdf_bytes: Conteúdo binário do PDF.
        user_id: ID do utilizador Supabase.
        origem: Valor para o campo 'origem' ('Mobile', 'Email').
        tipo: 'Despesa' ou 'Receita'.
        observacoes: Texto livre opcional.

    Returns:
        FaturaCreateResponse com id e categoria.
    """
    # --- Extrair QR Code do PDF ---
    try:
        qr_string, png_bytes = extract_qr_from_pdf(pdf_bytes)
    except PDFProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar o PDF: {exc.message}",
        )

    # --- Parse da string QR ---
    try:
        qr_data = parse_qr_string(qr_string)
    except QRParseError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Erro no parse do QR Code: {exc.message}",
        )

    atcud = qr_data["atcud"]
    data_fatura = qr_data["data_fatura"]

    # --- Verificar duplicado ---
    try:
        exists = await asyncio.to_thread(supabase_client.fatura_exists, atcud, user_id)
        if exists:
            raise HTTPException(
                status_code=409,
                detail=f"Fatura com ATCUD '{atcud}' já existe.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro ao verificar duplicado")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao verificar duplicado.",
        )

    # --- Upload do PDF para Storage ---
    storage_path = _build_storage_path(origem, data_fatura, atcud, "pdf", user_id)

    try:
        url_documento = await asyncio.to_thread(
            supabase_client.upload_documento,
            storage_path, pdf_bytes, "application/pdf",
        )
    except Exception:
        logger.exception("Erro no upload para Storage")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar o documento no Storage.",
        )

    # --- Inferir categoria via AI + nome do emissor (ambos em threads separadas) ---
    categoria = await asyncio.to_thread(ai_client.inferir_categoria, png_bytes, "image/png")
    nome_emissor = await asyncio.to_thread(get_nome_emissor, qr_data["nif_emissor"])

    # --- Inserir na DB ---
    fatura_data = {
        "atcud": atcud,
        "raw_qr_string": qr_data["raw_qr_string"],
        "tipo": tipo,
        "nif_emissor": qr_data["nif_emissor"],
        "data_fatura": data_fatura,
        "valor_total": str(qr_data["valor_total"]),
        "imposto_total": str(qr_data["imposto_total"]),
        "categoria": categoria,
        "url_documento": url_documento,
        "origem": origem,
        "nome_emissor": nome_emissor,
        "observacoes": observacoes,
    }

    try:
        registo = await asyncio.to_thread(supabase_client.insert_fatura, fatura_data, user_id)
    except Exception:
        logger.exception("Erro ao inserir fatura na DB")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar a fatura na base de dados.",
        )

    return FaturaCreateResponse(id=registo["id"], categoria=categoria)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/mobile", response_model=FaturaCreateResponse, status_code=201)
async def criar_fatura_mobile(
    qr_data: str = Form(...),
    tipo: str = Form(...),
    observacoes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Fluxo A — App Mobile.

    Recebe multipart/form-data com:
    - qr_data: JSON string com os campos extraídos do QR Code.
    - tipo: 'Despesa' ou 'Receita'.
    - file: Imagem JPEG/PNG do talão.
    """
    user_id = current_user.id
    logger.info("Recebida requisição POST /mobile para criar fatura. User: %s", user_id)

    # --- Validar tipo ---
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Campo 'tipo' inválido: '{tipo}'. Valores aceites: {', '.join(TIPOS_VALIDOS)}.",
        )

    # --- Parse e validação do qr_data ---
    try:
        qr_dict = json.loads(qr_data)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Campo 'qr_data' não é JSON válido: {exc}",
        )

    try:
        qr_payload = QRDataPayload(**qr_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Campos do QR inválidos: {exc}",
        )

    # --- Verificar duplicado ---
    try:
        exists = await asyncio.to_thread(supabase_client.fatura_exists, qr_payload.atcud, user_id)
        if exists:
            raise HTTPException(
                status_code=409,
                detail=f"Fatura com ATCUD '{qr_payload.atcud}' já existe.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro ao verificar duplicado no fluxo mobile")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao verificar duplicado.",
        )

    # --- Ler ficheiro ---
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao ler o ficheiro enviado: {exc}",
        )

    _validate_upload_size(file_bytes)

    # --- Determinar extensão e content type ---
    content_type = file.content_type or "image/jpeg"
    ext = "png" if "png" in content_type else "jpg"

    # --- Converter data_fatura de YYYYMMDD para YYYY-MM-DD ---
    data_fatura_raw = qr_payload.data_fatura
    if len(data_fatura_raw) == 8 and data_fatura_raw.isdigit():
        data_fatura_iso = f"{data_fatura_raw[:4]}-{data_fatura_raw[4:6]}-{data_fatura_raw[6:8]}"
    else:
        data_fatura_iso = data_fatura_raw

    # --- Upload para Storage ---
    storage_path = _build_storage_path("Mobile", data_fatura_iso, qr_payload.atcud, ext, user_id)

    try:
        url_documento = await asyncio.to_thread(
            supabase_client.upload_documento,
            storage_path, file_bytes, content_type,
        )
    except Exception:
        logger.exception("Erro no upload para Storage no fluxo mobile")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar o documento no Storage.",
        )

    # --- Inferir categoria via AI (Groq/Llama) ---
    categoria = await asyncio.to_thread(ai_client.inferir_categoria, file_bytes, content_type)
    nome_emissor = await asyncio.to_thread(get_nome_emissor, qr_payload.nif_emissor)
    observacoes_limpa = observacoes.strip() if observacoes and observacoes.strip() else None

    # --- Inserir na DB ---
    fatura_data = {
        "atcud": qr_payload.atcud,
        "raw_qr_string": qr_payload.raw_qr_string,
        "tipo": tipo,
        "nif_emissor": qr_payload.nif_emissor,
        "data_fatura": data_fatura_iso,
        "valor_total": str(qr_payload.valor_total),
        "imposto_total": str(qr_payload.imposto_total),
        "categoria": categoria,
        "url_documento": url_documento,
        "origem": "Mobile",
        "nome_emissor": nome_emissor,
        "observacoes": observacoes_limpa,
    }

    try:
        registo = await asyncio.to_thread(supabase_client.insert_fatura, fatura_data, user_id)
    except Exception:
        logger.exception("Erro ao inserir fatura na DB no fluxo mobile")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar a fatura na base de dados.",
        )

    return FaturaCreateResponse(id=registo["id"], categoria=categoria)


@router.post("/email", response_model=FaturaCreateResponse, status_code=201)
async def criar_fatura_email(
    tipo: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Fluxo B — PDF recebido por email.

    Recebe multipart/form-data com:
    - tipo: 'Despesa' ou 'Receita'.
    - file: Ficheiro PDF da fatura.
    """
    user_id = current_user.id
    logger.info("Recebida requisição POST /email para processar PDF da fatura. User: %s", user_id)

    # --- Validar tipo ---
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Campo 'tipo' inválido: '{tipo}'. Valores aceites: {', '.join(TIPOS_VALIDOS)}.",
        )

    # --- Ler PDF ---
    try:
        pdf_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao ler o ficheiro PDF enviado: {exc}",
        )

    _validate_upload_size(pdf_bytes)

    return await _process_pdf_and_save(
        pdf_bytes=pdf_bytes,
        user_id=user_id,
        origem="Email",
        tipo=tipo,
    )


@router.post("/pdf", response_model=FaturaCreateResponse, status_code=201)
async def criar_fatura_pdf(
    file: UploadFile = File(...),
    observacoes: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """
    Fluxo C — Submissão manual de PDF pela aplicação web.

    Recebe multipart/form-data com:
    - file: Ficheiro PDF da fatura.
    - observacoes: Texto livre (opcional).

    O tipo é forçado a 'Despesa' (regra de negócio).
    """
    user_id = current_user.id
    logger.info("Recebida requisição POST /pdf para processar PDF manual. User: %s", user_id)

    # --- Validar que é PDF ---
    content_type = file.content_type or ""
    if "pdf" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="Apenas ficheiros PDF são aceites neste endpoint.",
        )

    # --- Ler PDF ---
    try:
        pdf_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao ler o ficheiro PDF enviado: {exc}",
        )

    _validate_upload_size(pdf_bytes)

    observacoes_limpa = observacoes.strip() if observacoes and observacoes.strip() else None

    return await _process_pdf_and_save(
        pdf_bytes=pdf_bytes,
        user_id=user_id,
        origem="Email",
        tipo="Despesa",  # REGRA DE NEGÓCIO: sempre 'Despesa'
        observacoes=observacoes_limpa,
    )
