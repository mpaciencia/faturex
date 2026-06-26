"""
Processamento de PDFs para extração de QR Code.

Usa PyMuPDF (fitz) para renderizar a primeira página como PNG em memória.
Usa pyzbar para decodificar o QR Code da imagem renderizada.
Devolve a string bruta do QR e os bytes da imagem PNG.
"""

import io

import fitz  # PyMuPDF
from pyzbar.pyzbar import decode as pyzbar_decode
from PIL import Image


class PDFProcessingError(Exception):
    """Exceção lançada quando o processamento do PDF falha."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def extract_qr_from_pdf(pdf_bytes: bytes) -> tuple[str, bytes]:
    """
    Renderiza a primeira página do PDF como imagem PNG em memória
    e decodifica o QR Code presente na imagem.

    Args:
        pdf_bytes: Conteúdo binário do ficheiro PDF.

    Returns:
        Tuplo (qr_string, png_bytes):
            - qr_string: String bruta decodificada do QR Code.
            - png_bytes: Bytes da imagem PNG da primeira página.

    Raises:
        PDFProcessingError: Se o PDF não puder ser aberto, não tiver páginas,
                           ou não contiver um QR Code legível.
    """
    # Abrir o PDF a partir dos bytes (sem escrever ficheiros em disco)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFProcessingError(
            f"Não foi possível abrir o ficheiro PDF: {exc}"
        )

    if doc.page_count == 0:
        doc.close()
        raise PDFProcessingError("O ficheiro PDF não contém nenhuma página.")

    # Renderizar a primeira página como pixmap com resolução suficiente para QR
    try:
        page = doc[0]
        # DPI elevado (300) para garantir legibilidade do QR Code
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
    except Exception as exc:
        doc.close()
        raise PDFProcessingError(
            f"Erro ao renderizar a primeira página do PDF: {exc}"
        )

    # Converter pixmap para bytes PNG em memória
    png_bytes = pix.tobytes(output="png")
    doc.close()

    # Decodificar QR Code da imagem PNG usando pyzbar
    try:
        image = Image.open(io.BytesIO(png_bytes))
        decoded_objects = pyzbar_decode(image)
    except Exception as exc:
        raise PDFProcessingError(
            f"Erro ao decodificar QR Code da imagem: {exc}"
        )

    if not decoded_objects:
        raise PDFProcessingError(
            "Não foi encontrado nenhum QR Code na primeira página do PDF."
        )

    # Usar o primeiro QR Code encontrado
    qr_string = decoded_objects[0].data.decode("utf-8")

    if not qr_string.strip():
        raise PDFProcessingError(
            "O QR Code encontrado está vazio ou ilegível."
        )

    return qr_string, png_bytes
