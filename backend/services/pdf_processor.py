"""
Processamento de PDFs para extração de QR Code.

Usa PyMuPDF (fitz) para renderizar a primeira página como PNG em memória.
Usa pyzbar para decodificar o QR Code da imagem renderizada.
Devolve a string bruta do QR e os bytes da imagem PNG.
"""

import io

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

    try:
        # Renderizar a primeira página como pixmap com resolução suficiente para QR
        try:
            page = doc[0]
            # DPI elevado (300) para garantir legibilidade do QR Code
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
        except Exception as exc:
            raise PDFProcessingError(
                f"Erro ao renderizar a primeira página do PDF: {exc}"
            )

        # Converter pixmap da primeira página para bytes PNG em memória
        png_bytes = pix.tobytes(output="png")

        # Procurar o QR em todas as páginas; alguns PDFs incluem a capa na primeira.
        qr_string = ""
        qr_detector = cv2.QRCodeDetector() if cv2 is not None else None

        for page_index in range(doc.page_count):
            page = doc[page_index]
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes(output="png")

            if qr_detector is not None and np is not None:
                image_array = np.frombuffer(image_bytes, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
                if image is not None:
                    decoded_text, _, _ = qr_detector.detectAndDecode(image)
                    if decoded_text and decoded_text.strip():
                        qr_string = decoded_text.strip()
                        break

            if pyzbar_decode is not None:
                image = Image.open(io.BytesIO(image_bytes))
                decoded_objects = pyzbar_decode(image)

                if decoded_objects:
                    qr_string = decoded_objects[0].data.decode("utf-8")
                    if qr_string.strip():
                        break

        if not qr_string.strip():
            raise PDFProcessingError(
                "Não foi encontrado nenhum QR Code legível em nenhuma página do PDF."
            )

        return qr_string, png_bytes
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError(f"Erro ao decodificar QR Code da imagem: {exc}")
    finally:
        doc.close()
