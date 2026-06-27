"""
Rotas de faturas — POST /api/faturas/mobile e POST /api/faturas/email.

Os routers apenas orquestram serviços. Nenhuma lógica de negócio aqui.
"""

import json
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models.schemas import FaturaCreateResponse, QRDataPayload, TIPOS_VALIDOS
from services import gemini_client, supabase_client
from services.nif_service import get_nome_emissor
from services.pdf_processor import PDFProcessingError, extract_qr_from_pdf
from services.qr_parser import QRParseError, parse_qr_string

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/faturas", tags=["Faturas"])


def _build_storage_path(origem: str, data_fatura: str, atcud: str, ext: str) -> str:
    """
    Constrói o path no Storage: {origem}/{ano}/{mes}/{atcud}.{ext}

    Args:
        origem: 'Mobile' ou 'Email'.
        data_fatura: Data no formato 'YYYY-MM-DD'.
        atcud: Código único AT.
        ext: Extensão do ficheiro (sem ponto).
    """
    ano = data_fatura[:4]
    mes = data_fatura[5:7]
    return f"{origem}/{ano}/{mes}/{atcud}.{ext}"


@router.post("/mobile", response_model=FaturaCreateResponse, status_code=201)
async def criar_fatura_mobile(
    qr_data: str = Form(...),
    tipo: str = Form(...),
    observacoes: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Fluxo A — App Mobile.

    Recebe multipart/form-data com:
    - qr_data: JSON string com os campos extraídos do QR Code.
    - tipo: 'Despesa' ou 'Receita'.
    - file: Imagem JPEG/PNG do talão.
    """
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
        if supabase_client.fatura_exists(qr_payload.atcud):
            raise HTTPException(
                status_code=409,
                detail=f"Fatura com ATCUD '{qr_payload.atcud}' já existe.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao verificar duplicado: %s", exc)
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
    storage_path = _build_storage_path("Mobile", data_fatura_iso, qr_payload.atcud, ext)

    try:
        url_documento = supabase_client.upload_documento(
            path=storage_path,
            content=file_bytes,
            content_type=content_type,
        )
    except Exception as exc:
        logger.error("Erro no upload para Storage: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar o documento no Storage.",
        )

    # --- Inferir categoria via Gemini ---
    categoria = gemini_client.inferir_categoria(file_bytes, mime_type=content_type)
    nome_emissor = get_nome_emissor(qr_payload.nif_emissor)
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
        registo = supabase_client.insert_fatura(fatura_data)
    except Exception as exc:
        logger.error("Erro ao inserir fatura na DB: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar a fatura na base de dados.",
        )

    return FaturaCreateResponse(id=registo["id"], categoria=categoria)


@router.post("/email", response_model=FaturaCreateResponse, status_code=201)
async def criar_fatura_email(
    tipo: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Fluxo B — Gmail / Google Apps Script.

    Recebe multipart/form-data com:
    - tipo: 'Despesa' ou 'Receita'.
    - file: Ficheiro PDF da fatura.
    """
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
        if supabase_client.fatura_exists(atcud):
            raise HTTPException(
                status_code=409,
                detail=f"Fatura com ATCUD '{atcud}' já existe.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao verificar duplicado: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao verificar duplicado.",
        )

    # --- Upload do PDF original para Storage ---
    storage_path = _build_storage_path("Email", data_fatura, atcud, "pdf")

    try:
        url_documento = supabase_client.upload_documento(
            path=storage_path,
            content=pdf_bytes,
            content_type="application/pdf",
        )
    except Exception as exc:
        logger.error("Erro no upload para Storage: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar o documento no Storage.",
        )

    # --- Inferir categoria via Gemini (usando PNG da primeira página) ---
    categoria = gemini_client.inferir_categoria(png_bytes, mime_type="image/png")
    nome_emissor = get_nome_emissor(qr_data["nif_emissor"])

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
        "origem": "Email",
        "nome_emissor": nome_emissor,
        "observacoes": None,
    }

    try:
        registo = supabase_client.insert_fatura(fatura_data)
    except Exception as exc:
        logger.error("Erro ao inserir fatura na DB: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao guardar a fatura na base de dados.",
        )

    return FaturaCreateResponse(id=registo["id"], categoria=categoria)
