import logging
import unittest
from unittest.mock import MagicMock, patch

from routes import invoices, reports
from services import ai_client, pdf_processor, supabase_client
from services.pdf_processor import PDFProcessingError


class LoggingFlowTests(unittest.TestCase):

    # ----------------------------------------------------
    # SUCCESS SCENARIOS
    # ----------------------------------------------------
    @patch("services.ai_client._client")
    def test_ai_client_success_logs(self, mock_groq_client):
        """Testa se a inferência de categoria via IA loga INFO e retorna a categoria correta."""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"categoria": "Material de Escritório"}'
        mock_groq_client.chat.completions.create.return_value.choices = [mock_choice]

        with self.assertLogs("services.ai_client", level="INFO") as log_capture:
            categoria = ai_client.inferir_categoria(b"fake_image_bytes", "image/png")

        self.assertEqual(categoria, "Material de Escritório")
        self.assertTrue(
            any("Iniciando inferência de categoria via IA" in log for log in log_capture.output)
        )

    @patch("services.supabase_client._client")
    def test_supabase_insert_success_logs(self, mock_sb_client):
        """Testa se a inserção no Supabase loga INFO para início e sucesso da operação."""
        mock_response = MagicMock()
        mock_response.data = [{"id": 123, "atcud": "ATCUD-TEST-123"}]
        mock_sb_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with self.assertLogs("services.supabase_client", level="INFO") as log_capture:
            res = supabase_client.insert_fatura({"atcud": "ATCUD-TEST-123", "tipo": "Despesa"})

        self.assertEqual(res["id"], 123)
        self.assertTrue(
            any("A tentar inserir fatura no Supabase" in log for log in log_capture.output)
        )
        self.assertTrue(
            any("Fatura inserida com sucesso no Supabase" in log for log in log_capture.output)
        )

    # ----------------------------------------------------
    # INPUT FAILURE SCENARIOS
    # ----------------------------------------------------
    def test_pdf_processor_corrupt_file_logs_exception(self):
        """Testa se o processamento de arquivo PDF inválido dispara e loga uma exceção."""
        with self.assertRaises(PDFProcessingError):
            with self.assertLogs("services.pdf_processor", level="ERROR") as log_capture:
                pdf_processor.extract_qr_from_pdf(b"not_a_pdf_file_bytes")

        self.assertTrue(
            any("Não foi possível abrir o ficheiro PDF a partir dos bytes" in log for log in log_capture.output)
        )

    # ----------------------------------------------------
    # EXTERNAL API FAILURE SCENARIOS
    # ----------------------------------------------------
    @patch("services.ai_client._client")
    def test_ai_client_api_error_logs_exception(self, mock_groq_client):
        """Testa se uma falha de rede/API na IA loga a stack trace (exception) e cai no fallback."""
        mock_groq_client.chat.completions.create.side_effect = Exception("Groq API Timeout")

        with self.assertLogs("services.ai_client", level="ERROR") as log_capture:
            categoria = ai_client.inferir_categoria(b"fake_image_bytes", "image/png")

        self.assertEqual(categoria, "Outros")
        self.assertTrue(
            any("Erro inesperado na chamada ao serviço de IA" in log for log in log_capture.output)
        )

    @patch("services.supabase_client._client")
    def test_supabase_connection_error_logs_exception(self, mock_sb_client):
        """Testa se uma falha de ligação ao Supabase loga a stack trace como exceção."""
        mock_sb_client.table.side_effect = Exception("Supabase DB Connection Refused")

        with self.assertRaises(Exception):
            with self.assertLogs("services.supabase_client", level="ERROR") as log_capture:
                supabase_client.insert_fatura({"atcud": "ATCUD-ERROR", "tipo": "Despesa"})

        self.assertTrue(
            any("Erro ao inserir fatura no Supabase" in log for log in log_capture.output)
        )
