"""
Parse da string QR Code AT (formato português).

Campos separados por '*', com chaves como A:, B:, F:, O:, VT:, I1:, J1:, K1:, etc.
Extrai: atcud, nif_emissor, data_fatura, valor_total, imposto_total.
"""

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

    # Validar que a data é coerente (ano, mês, dia)
    try:
        ano = int(data_fatura_raw[:4])
        mes = int(data_fatura_raw[4:6])
        dia = int(data_fatura_raw[6:8])
        if not (1 <= mes <= 12 and 1 <= dia <= 31 and ano >= 2000):
            raise ValueError
    except ValueError:
        raise QRParseError(
            f"Campo 'F' (data da fatura) contém data inválida: '{data_fatura_raw}'."
        )

    # Converter para formato ISO (YYYY-MM-DD) para uso posterior
    data_fatura = f"{data_fatura_raw[:4]}-{data_fatura_raw[4:6]}-{data_fatura_raw[6:8]}"

    # --- ATCUD (campo O:) ---
    atcud = campos.get("O")
    if not atcud:
        raise QRParseError("Campo obrigatório 'O' (ATCUD) ausente no QR Code.")

    # --- Valor total com IVA (campo VT:) ---
    valor_total_raw = campos.get("VT")
    if not valor_total_raw:
        raise QRParseError("Campo obrigatório 'VT' (valor total) ausente no QR Code.")

    try:
        valor_total = Decimal(valor_total_raw)
    except InvalidOperation:
        raise QRParseError(
            f"Campo 'VT' (valor total) não é um número válido: '{valor_total_raw}'."
        )

    # --- Imposto total (IVA) — soma de I1:, J1:, K1: ---
    # Correspondem às três taxas de IVA possíveis (reduzida, intermédia, normal).
    # Podem estar todas presentes ou apenas algumas.
    imposto_total = Decimal("0")
    campos_iva = ["I1", "J1", "K1"]
    for campo_iva in campos_iva:
        valor_iva_raw = campos.get(campo_iva)
        if valor_iva_raw:
            try:
                imposto_total += Decimal(valor_iva_raw)
            except InvalidOperation:
                raise QRParseError(
                    f"Campo '{campo_iva}' (IVA) não é um número válido: '{valor_iva_raw}'."
                )

    return {
        "atcud": atcud,
        "nif_emissor": nif_emissor,
        "data_fatura": data_fatura,
        "valor_total": valor_total,
        "imposto_total": imposto_total,
        "raw_qr_string": raw_qr.strip(),
    }
