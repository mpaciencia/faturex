"""
Rota de relatórios — GET /api/relatorios.

Gera ficheiro .xlsx com openpyxl, organizado por Despesas e Receitas.
"""

import io
import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

from services import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])


def _build_sheet(
    wb: Workbook,
    sheet_name: str,
    faturas: list[dict],
) -> None:
    """
    Constrói uma folha no workbook com faturas agrupadas por categoria,
    incluindo subtotais por categoria e total geral.

    Colunas: Data | NIF Emissor | Categoria | IVA (€) | Total (€)
    """
    ws = wb.create_sheet(title=sheet_name)

    # --- Estilos ---
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    subtotal_font = Font(name="Calibri", bold=True, size=10)
    subtotal_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

    total_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    total_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # --- Headers ---
    headers = ["Data", "NIF Emissor", "Categoria", "IVA (€)", "Total (€)"]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # --- Agrupar faturas por categoria ---
    por_categoria: dict[str, list[dict]] = {}
    for fatura in faturas:
        cat = fatura.get("categoria", "Outros")
        por_categoria.setdefault(cat, []).append(fatura)

    # Ordenar categorias alfabeticamente
    categorias_ordenadas = sorted(por_categoria.keys())

    row_idx = 2
    total_geral_iva = Decimal("0")
    total_geral_valor = Decimal("0")

    for categoria in categorias_ordenadas:
        faturas_cat = por_categoria[categoria]
        subtotal_iva = Decimal("0")
        subtotal_valor = Decimal("0")

        for fatura in faturas_cat:
            iva = Decimal(str(fatura.get("imposto_total", "0")))
            total = Decimal(str(fatura.get("valor_total", "0")))

            ws.cell(row=row_idx, column=1, value=fatura.get("data_fatura", "")).border = thin_border
            ws.cell(row=row_idx, column=2, value=fatura.get("nif_emissor", "")).border = thin_border
            ws.cell(row=row_idx, column=3, value=categoria).border = thin_border

            cell_iva = ws.cell(row=row_idx, column=4, value=float(iva))
            cell_iva.number_format = '#,##0.00'
            cell_iva.border = thin_border

            cell_total = ws.cell(row=row_idx, column=5, value=float(total))
            cell_total.number_format = '#,##0.00'
            cell_total.border = thin_border

            subtotal_iva += iva
            subtotal_valor += total
            row_idx += 1

        # Linha de subtotal da categoria
        ws.cell(row=row_idx, column=1, value="").border = thin_border
        ws.cell(row=row_idx, column=2, value="").border = thin_border

        cell_sub_label = ws.cell(row=row_idx, column=3, value=f"Subtotal — {categoria}")
        cell_sub_label.font = subtotal_font
        cell_sub_label.fill = subtotal_fill
        cell_sub_label.border = thin_border

        cell_sub_iva = ws.cell(row=row_idx, column=4, value=float(subtotal_iva))
        cell_sub_iva.number_format = '#,##0.00'
        cell_sub_iva.font = subtotal_font
        cell_sub_iva.fill = subtotal_fill
        cell_sub_iva.border = thin_border

        cell_sub_total = ws.cell(row=row_idx, column=5, value=float(subtotal_valor))
        cell_sub_total.number_format = '#,##0.00'
        cell_sub_total.font = subtotal_font
        cell_sub_total.fill = subtotal_fill
        cell_sub_total.border = thin_border

        total_geral_iva += subtotal_iva
        total_geral_valor += subtotal_valor
        row_idx += 1

    # --- Linha de total geral ---
    ws.cell(row=row_idx, column=1, value="").border = thin_border
    ws.cell(row=row_idx, column=2, value="").border = thin_border

    cell_total_label = ws.cell(row=row_idx, column=3, value="TOTAL GERAL")
    cell_total_label.font = total_font
    cell_total_label.fill = total_fill
    cell_total_label.border = thin_border

    cell_total_iva = ws.cell(row=row_idx, column=4, value=float(total_geral_iva))
    cell_total_iva.number_format = '#,##0.00'
    cell_total_iva.font = total_font
    cell_total_iva.fill = total_fill
    cell_total_iva.border = thin_border

    cell_total_val = ws.cell(row=row_idx, column=5, value=float(total_geral_valor))
    cell_total_val.number_format = '#,##0.00'
    cell_total_val.font = total_font
    cell_total_val.fill = total_fill
    cell_total_val.border = thin_border

    # --- Ajustar largura das colunas ---
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 35
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14


@router.get("")
async def gerar_relatorio(
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
):
    """
    Fluxo C — Geração de relatório Excel.

    Query params: data_inicio e data_fim no formato YYYY-MM-DD.
    Devolve ficheiro .xlsx com folhas 'Despesas' e 'Receitas'.
    """
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=400,
            detail="'data_inicio' não pode ser posterior a 'data_fim'.",
        )

    # --- Consultar faturas no período ---
    try:
        faturas = supabase_client.get_faturas_by_period(
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
        )
    except Exception as exc:
        logger.error("Erro ao consultar faturas: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao consultar faturas.",
        )

    # --- Separar por tipo ---
    despesas = [f for f in faturas if f.get("tipo") == "Despesa"]
    receitas = [f for f in faturas if f.get("tipo") == "Receita"]

    # --- Construir workbook ---
    wb = Workbook()
    # Remover folha padrão criada automaticamente
    wb.remove(wb.active)

    _build_sheet(wb, "Despesas", despesas)
    _build_sheet(wb, "Receitas", receitas)

    # --- Serializar para bytes em memória ---
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # --- Nome do ficheiro ---
    filename = f"relatorio_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        content=buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
