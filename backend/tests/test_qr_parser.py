from pathlib import Path
import unittest

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

    def test_extracts_qr_from_second_pdf_page(self) -> None:
        pdf_path = Path(__file__).resolve().parents[2] / "fatura2.pdf"
        pdf_bytes = pdf_path.read_bytes()

        qr_string, _ = extract_qr_from_pdf(pdf_bytes)
        parsed = parse_qr_string(qr_string)

        self.assertEqual(parsed["atcud"], "J6HR5DFX-1771205")
        self.assertEqual(parsed["nif_emissor"], "515463850")
        self.assertEqual(parsed["data_fatura"], "2026-05-15")
        self.assertEqual(str(parsed["valor_total"]), "11.48")
        self.assertEqual(str(parsed["imposto_total"]), "0.65")


if __name__ == "__main__":
    unittest.main()