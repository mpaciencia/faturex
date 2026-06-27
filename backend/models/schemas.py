"""
Modelos Pydantic de entrada e saída.

Usa Decimal para todos os valores monetários — nunca float.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Payload de entrada — Fluxo Mobile (qr_data é enviado como JSON string)
# ---------------------------------------------------------------------------
class QRDataPayload(BaseModel):
    """Campos extraídos do QR Code pela app mobile."""
    atcud: str
    nif_emissor: str
    data_fatura: str  # formato YYYYMMDD conforme QR AT
    valor_total: Decimal
    imposto_total: Decimal
    raw_qr_string: str
    observacoes: Optional[str] = None


# ---------------------------------------------------------------------------
# Payload de entrada — Fluxo Email (apenas tipo; o QR é extraído do PDF)
# ---------------------------------------------------------------------------
# O campo 'tipo' e o ficheiro PDF são enviados via multipart/form-data.
# Não existe um modelo Pydantic dedicado porque os campos vêm de Form().


# ---------------------------------------------------------------------------
# Modelo de resposta de criação (201 Created)
# ---------------------------------------------------------------------------
class FaturaCreateResponse(BaseModel):
    """Resposta devolvida após inserção bem-sucedida de uma fatura."""
    id: str
    categoria: str


class FaturaCreateInput(BaseModel):
    """Campos adicionais do formulário de criação de fatura."""
    observacoes: Optional[str] = None


# ---------------------------------------------------------------------------
# Query params do relatório
# ---------------------------------------------------------------------------
class RelatorioParams(BaseModel):
    """Parâmetros de filtragem para geração do relatório Excel."""
    data_inicio: date
    data_fim: date


# ---------------------------------------------------------------------------
# Categorias permitidas (fonte de verdade: secção 7 do agent_rules.md)
# ---------------------------------------------------------------------------
CATEGORIAS_VALIDAS: set[str] = {
    "Material de Escritório",
    "Deslocações e Transportes",
    "Alimentação e Representação",
    "Telecomunicações",
    "Software e Serviços Digitais",
    "Equipamento e Ferramentas",
    "Obras e Materiais de Construção",
    "Serviços Externos",
    "Publicidade e Marketing",
    "Outros",
}

TIPOS_VALIDOS: set[str] = {"Despesa", "Receita"}
