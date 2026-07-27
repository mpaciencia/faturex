"""
Script de backfill: re-executa a IA de categorização em faturas com categoria "Outros".

Muitas faturas ficaram como "Outros" porque a API Groq deu timeout ou a resposta
veio mal formatada. Este script descarrega o documento de cada fatura, extrai a
imagem (renderizando o PDF se necessário) e volta a chamar o modelo de IA.

Utilização:
    venv\\Scripts\\python backfill_categorias.py             # executa com atualizações
    venv\\Scripts\\python backfill_categorias.py --dry-run   # apenas mostra o que faria
"""

import io
import sys
import time
import logging
import argparse

import fitz  # PyMuPDF

from services.supabase_client import _client, download_documento, storage_path_from_public_url
from services.ai_client import inferir_categoria

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# Pausa entre chamadas à API Groq para evitar rate limits (segundos)
DELAY_ENTRE_CHAMADAS = 20

# Número máximo de retries por fatura em caso de erro
MAX_RETRIES = 2


def _render_pdf_first_page(pdf_bytes: bytes) -> bytes:
    """Renderiza a 1ª página de um PDF como PNG (300 DPI)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.page_count == 0:
            raise ValueError("PDF sem páginas")
        page = doc[0]
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes(output="png")
    finally:
        doc.close()


def _guess_mime_type(url: str) -> str:
    """Adivinha o MIME type a partir da extensão na URL do documento."""
    url_lower = url.lower()
    if url_lower.endswith(".png"):
        return "image/png"
    if url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
        return "image/jpeg"
    if url_lower.endswith(".pdf"):
        return "application/pdf"
    # Fallback — assume imagem JPEG (o mais comum no fluxo mobile)
    return "image/jpeg"


def main():
    parser = argparse.ArgumentParser(
        description="Re-executa a IA de categorização em faturas com categoria 'Outros'."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o que faria, sem alterar a base de dados.",
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("\n🔍 MODO DRY-RUN — nenhuma alteração será feita na base de dados.\n")

    # 1. Buscar todas as faturas com categoria "Outros"
    print("📂 A buscar faturas com categoria 'Outros'...")
    response = (
        _client.table("faturas")
        .select("id, atcud, url_documento, categoria, nome_emissor, nif_emissor")
        .eq("categoria", "Outros")
        .execute()
    )
    faturas = response.data
    total = len(faturas)

    if total == 0:
        print("✅ Nenhuma fatura com categoria 'Outros' encontrada. Nada a fazer.")
        return

    print(f"📋 Encontradas {total} faturas com categoria 'Outros'.\n")

    # Contadores
    atualizadas = 0
    mantidas = 0
    erros = 0
    skipped = 0

    for i, fatura in enumerate(faturas, 1):
        fatura_id = fatura["id"]
        atcud = fatura.get("atcud", "?")
        url_doc = fatura.get("url_documento", "")
        emissor = fatura.get("nome_emissor") or fatura.get("nif_emissor") or "?"

        print(f"[{i}/{total}] ATCUD: {atcud} | Emissor: {emissor}")

        # Faturas manuais sem documento real
        if not url_doc or url_doc.startswith("manual://"):
            print(f"  ⏭ Sem documento para analisar (url: {url_doc}). A saltar.")
            skipped += 1
            continue

        # 2. Descarregar o documento do Storage
        try:
            storage_path = storage_path_from_public_url(url_doc)
            doc_bytes = download_documento(storage_path)
        except Exception as exc:
            print(f"  ❌ Erro ao descarregar documento: {exc}")
            erros += 1
            continue

        # 3. Preparar imagem para a IA
        mime_type = _guess_mime_type(url_doc)

        if mime_type == "application/pdf":
            try:
                image_bytes = _render_pdf_first_page(doc_bytes)
                mime_type = "image/png"
            except Exception as exc:
                print(f"  ❌ Erro ao renderizar PDF: {exc}")
                erros += 1
                continue
        else:
            image_bytes = doc_bytes

        # 4. Chamar a IA (com retries)
        nova_categoria = None
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                nova_categoria = inferir_categoria(image_bytes, mime_type)
                break
            except Exception as exc:
                print(f"  ⚠ Tentativa {tentativa}/{MAX_RETRIES} falhou: {exc}")
                if tentativa < MAX_RETRIES:
                    time.sleep(DELAY_ENTRE_CHAMADAS)

        if nova_categoria is None:
            print(f"  ❌ Todas as tentativas falharam. A saltar.")
            erros += 1
            continue

        # 5. Verificar se a nova categoria é diferente
        if nova_categoria == "Outros":
            print(f"  ➡ IA manteve 'Outros'.")
            mantidas += 1
        else:
            print(f"  ✨ Nova categoria: {nova_categoria}")
            if not dry_run:
                try:
                    _client.table("faturas").update(
                        {"categoria": nova_categoria}
                    ).eq("id", fatura_id).execute()
                    atualizadas += 1
                except Exception as exc:
                    print(f"  ❌ Erro ao atualizar na BD: {exc}")
                    erros += 1
            else:
                atualizadas += 1  # conta como "seria atualizada" no dry-run

        # Pausa entre chamadas
        if i < total:
            time.sleep(DELAY_ENTRE_CHAMADAS)

    # Resumo final
    print(f"\n{'='*60}")
    print(f"  RESUMO {'(DRY-RUN) ' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Total analisadas:   {total}")
    print(f"  Saltadas (s/ doc):  {skipped}")
    print(f"  Re-categorizadas:   {atualizadas}")
    print(f"  Mantidas 'Outros':  {mantidas}")
    print(f"  Erros:              {erros}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
