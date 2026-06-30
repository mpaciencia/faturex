from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from services.pdf_processor import extract_qr_from_pdf
from services.qr_parser import QRParseError, parse_qr_string


class ParseQrStringTests(unittest.TestCase):
    def test_parses_required_at_fields(self) -> None:
        raw_qr = (
            "A:123456789*F:20250620*H:ATCUD-ABC-123*O:123.45*N:23.45*"
            "I1:PT*I7:100.00*I8:23.00*Q:HASH*R:CERT"
        )

        parsed = parse_qr_string(raw_qr)

        self.assertEqual(parsed["atcud"], "ATCUD-ABC-123")
        self.assertEqual(parsed["nif_emissor"], "123456789")
        self.assertEqual(parsed["data_fatura"], "2025-06-20")
        self.assertEqual(str(parsed["valor_total"]), "123.45")
        self.assertEqual(str(parsed["imposto_total"]), "23.45")
        self.assertEqual(parsed["raw_qr_string"], raw_qr)

    def test_rejects_missing_n_field(self) -> None:
        raw_qr = "A:123456789*F:20250620*H:ATCUD-ABC-123*O:123.45"

        with self.assertRaises(QRParseError) as context:
            parse_qr_string(raw_qr)

        self.assertIn("Campo obrigatório 'N'", str(context.exception))

    @patch("services.pdf_processor.fitz.open")
    @patch("services.pdf_processor.pyzbar_decode")
    @patch("services.pdf_processor.Image.open")
    def test_extracts_qr_from_second_pdf_page(self, mock_image_open, mock_pyzbar_decode, mock_fitz_open) -> None:
        # Setup mock document and pages
        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_fitz_open.return_value = mock_doc

        mock_page_0 = MagicMock()
        mock_page_1 = MagicMock()
        mock_doc.__getitem__.side_effect = [mock_page_0, mock_page_1]

        # Setup mock pixmaps
        mock_pix_0 = MagicMock()
        mock_pix_0.tobytes.return_value = b"fake_png_bytes_page0"
        mock_page_0.get_pixmap.return_value = mock_pix_0

        mock_pix_1 = MagicMock()
        mock_pix_1.tobytes.return_value = b"fake_png_bytes_page1"
        mock_page_1.get_pixmap.return_value = mock_pix_1

        # Setup mock decode function:
        # First page fails, second page succeeds
        mock_qr_obj = MagicMock()
        mock_qr_obj.data.decode.return_value = (
            "A:515463850*F:20260515*H:J6HR5DFX-1771205*O:11.48*N:0.65"
        )
        
        mock_pyzbar_decode.side_effect = [[], [mock_qr_obj]]

        # Force pyzbar usage in pdf_processor by mocking cv2 as None
        with patch("services.pdf_processor.cv2", None):
            qr_string, png_bytes = extract_qr_from_pdf(b"dummy_pdf_bytes")

        self.assertEqual(png_bytes, b"fake_png_bytes_page1")
        parsed = parse_qr_string(qr_string)

        self.assertEqual(parsed["atcud"], "J6HR5DFX-1771205")
        self.assertEqual(parsed["nif_emissor"], "515463850")
        self.assertEqual(parsed["data_fatura"], "2026-05-15")
        self.assertEqual(str(parsed["valor_total"]), "11.48")
        self.assertEqual(str(parsed["imposto_total"]), "0.65")


if __name__ == "__main__":
    unittest.main()