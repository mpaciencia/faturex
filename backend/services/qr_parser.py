"""
Parse da string QR Code AT (formato português).

Campos separados por '*', com chaves como A:, B:, F:, H:, I1:, I7:, I8:, N:, O:, Q:, R:, etc.
Extrai: atcud, nif_emissor, data_fatura, valor_total, imposto_total.

Especificação AT (Portaria n.º 195/2020):
    A:  NIF do emissor
    F:  Data da fatura (YYYYMMDD)
    H:  ATCUD (código de validação da série + número sequencial)
    I7: Base tributável à taxa normal
    I8: IVA à taxa normal
    N:  IVA total
    O:  Valor total do documento (bruto com IVA)
    Q:  Hash dos 4 caracteres
    R:  Número do certificado do software
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation


class QRParseError(Exception):
    """Exceção lançada quando o parse do QR Code AT falha."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def parse_qr_string(raw_qr: str) -> dict:
    """
    Faz parse da string bruta do QR Code AT e devolve um dicionário
    com os campos estruturados.

    Args:
        raw_qr: String bruta do QR Code (campos separados por '*').

    Returns:
        dict com chaves: atcud, nif_emissor, data_fatura, valor_total, imposto_total.

    Raises:
        QRParseError: Se algum campo obrigatório estiver ausente ou malformado.
    """
    if not raw_qr or not raw_qr.strip():
        raise QRParseError("String do QR Code está vazia.")

    # Construir dicionário chave→valor a partir dos segmentos separados por '*'
    campos: dict[str, str] = {}
    segmentos = raw_qr.strip().split("*")

    for segmento in segmentos:
        if ":" not in segmento:
            continue
        chave, _, valor = segmento.partition(":")
        campos[chave.strip()] = valor.strip()

    # --- NIF do emissor (campo A:) ---
    nif_emissor = campos.get("A")
    if not nif_emissor:
        raise QRParseError("Campo obrigatório 'A' (NIF do emissor) ausente no QR Code.")

    if not nif_emissor.isdigit() or len(nif_emissor) != 9:
        raise QRParseError(
            f"Campo 'A' (NIF do emissor) inválido: '{nif_emissor}'. "
            "Deve conter exatamente 9 dígitos."
        )

    # --- Data da fatura (campo F:, formato YYYYMMDD) ---
    data_fatura_raw = campos.get("F")
    if not data_fatura_raw:
        raise QRParseError("Campo obrigatório 'F' (data da fatura) ausente no QR Code.")

    if not data_fatura_raw.isdigit() or len(data_fatura_raw) != 8:
        raise QRParseError(
            f"Campo 'F' (data da fatura) inválido: '{data_fatura_raw}'. "
            "Formato esperado: YYYYMMDD."
        )

    # Validar que a data é coerente e existe no calendário.
    try:
        datetime.strptime(data_fatura_raw, "%Y%m%d")
    except ValueError:
        raise QRParseError(
            f"Campo 'F' (data da fatura) contém data inválida: '{data_fatura_raw}'."
        )

    # Converter para formato ISO (YYYY-MM-DD) para uso posterior
    data_fatura = f"{data_fatura_raw[:4]}-{data_fatura_raw[4:6]}-{data_fatura_raw[6:8]}"

    # --- ATCUD (campo H: conforme especificação AT - Portaria 195/2020) ---
    atcud = campos.get("H")
    if not atcud:
        raise QRParseError("Campo obrigatório 'H' (ATCUD) ausente no QR Code.")
    
    import re
    if not re.match(r"^[A-Za-z0-9\-]+$", atcud):
        raise QRParseError(
            f"Campo 'H' (ATCUD) inválido: '{atcud}'. "
            "Deve conter apenas letras, números e hífens."
        )

    # --- Valor total do documento (campo O: conforme especificação AT) ---
    valor_total_raw = campos.get("O")
    if not valor_total_raw:
        raise QRParseError("Campo obrigatório 'O' (valor total) ausente no QR Code.")

    try:
        valor_total = Decimal(valor_total_raw)
    except InvalidOperation:
        raise QRParseError(
            f"Campo 'O' (valor total) não é um número válido: '{valor_total_raw}'."
        )

    # --- Imposto total (campo N:) ---
    n_raw = campos.get("N")
    if not n_raw:
        raise QRParseError("Campo obrigatório 'N' (IVA total) ausente no QR Code.")

    try:
        imposto_total = Decimal(n_raw)
    except InvalidOperation:
        raise QRParseError(
            f"Campo 'N' (IVA total) não é um número válido: '{n_raw}'."
        )

    return {
        "atcud": atcud,
        "nif_emissor": nif_emissor,
        "data_fatura": data_fatura,
        "valor_total": valor_total,
        "imposto_total": imposto_total,
        "raw_qr_string": raw_qr.strip(),
    }
