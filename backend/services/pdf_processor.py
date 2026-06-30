"""
Processamento de PDFs para extração de QR Code.

Usa PyMuPDF (fitz) para renderizar a primeira página como PNG em memória.
Usa pyzbar para decodificar o QR Code da imagem renderizada.
Devolve a string bruta do QR e os bytes da imagem PNG.
"""

import io
import logging

import fitz  # PyMuPDF
from PIL import Image

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - optional dependency fallback
    cv2 = None
    np = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:  # pragma: no cover - optional dependency fallback
    pyzbar_decode = None

logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Exceção lançada quando o processamento do PDF falha."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def extract_qr_from_pdf(pdf_bytes: bytes) -> tuple[str, bytes]:
    """
    Renderiza as páginas do PDF como imagem PNG em memória, procura um QR Code nelas
    e devolve a string bruta do QR Code e os bytes da imagem PNG da página onde
    o QR Code foi detectado.

    Args:
        pdf_bytes: Conteúdo binário do ficheiro PDF.

    Returns:
        Tuplo (qr_string, png_bytes):
            - qr_string: String bruta decodificada do QR Code.
            - png_bytes: Bytes da imagem PNG da página onde o QR Code foi encontrado.

    Raises:
        PDFProcessingError: Se o PDF não puder ser aberto, não tiver páginas,
                           ou não contiver um QR Code legível.
    """
    logger.info("A iniciar processamento de PDF para extração de QR Code")
    # Abrir o PDF a partir dos bytes (sem escrever ficheiros em disco)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.exception("Não foi possível abrir o ficheiro PDF a partir dos bytes")
        raise PDFProcessingError(
            f"Não foi possível abrir o ficheiro PDF: {exc}"
        )

    if doc.page_count == 0:
        doc.close()
        logger.warning("Ficheiro PDF não contém páginas")
        raise PDFProcessingError("O ficheiro PDF não contém nenhuma página.")

    logger.info("PDF aberto com sucesso. Número de páginas: %d", doc.page_count)
    try:
        # Procurar o QR em todas as páginas
        qr_string = ""
        png_bytes = None
        qr_detector = cv2.QRCodeDetector() if cv2 is not None else None

        for page_index in range(doc.page_count):
            logger.info("A tentar extrair QR Code da página %d", page_index + 1)
            try:
                page = doc[page_index]
                # DPI elevado (300) para garantir legibilidade do QR Code
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                image_bytes = pix.tobytes(output="png")
            except Exception as exc:
                logger.exception("Erro ao renderizar a página %d do PDF", page_index + 1)
                continue  # tenta a próxima página se a renderização desta falhar

            found_qr = False

            if qr_detector is not None and np is not None:
                image_array = np.frombuffer(image_bytes, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
                if image is not None:
                    decoded_text, _, _ = qr_detector.detectAndDecode(image)
                    if decoded_text and decoded_text.strip():
                        qr_string = decoded_text.strip()
                        png_bytes = image_bytes
                        logger.info("QR Code detetado via OpenCV na página %d", page_index + 1)
                        found_qr = True

            if not found_qr and pyzbar_decode is not None:
                image = Image.open(io.BytesIO(image_bytes))
                decoded_objects = pyzbar_decode(image)

                if decoded_objects:
                    decoded_text = decoded_objects[0].data.decode("utf-8")
                    if decoded_text.strip():
                        qr_string = decoded_text.strip()
                        png_bytes = image_bytes
                        logger.info("QR Code detetado via Pyzbar na página %d", page_index + 1)
                        found_qr = True

            if found_qr:
                break

        if not qr_string.strip():
            logger.warning("Nenhum QR Code encontrado nas páginas do PDF")
            raise PDFProcessingError(
                "Não foi encontrado nenhum QR Code legível em nenhuma página do PDF."
            )

        logger.info("QR Code extraído com sucesso do PDF")
        return qr_string, png_bytes
    except PDFProcessingError:
        raise
    except Exception as exc:
        logger.exception("Erro inesperado ao decodificar QR Code da imagem")
        raise PDFProcessingError(f"Erro ao decodificar QR Code da imagem: {exc}")
    finally:
        doc.close()
