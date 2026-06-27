import { FATUREX_API_BASE_URL, FATUREX_API_KEY } from "../config";
import type { AtQrPayload, DocumentType } from "../utils/qrValidation";

export interface SubmitInvoiceInput {
  qrPayload: AtQrPayload;
  tipo: DocumentType;
  observacoes?: string;
  imageUri: string;
  imageName?: string;
  imageType?: string;
}

export interface SubmitInvoiceResult {
  id: string;
  categoria: string;
}

function guessFileName(imageUri: string): string {
  const fileName = imageUri.split("/").pop();
  return fileName && fileName.length > 0 ? fileName : "fatura.jpg";
}

function parseBackendError(text: string): string {
  if (!text.trim()) {
    return "Erro inesperado no backend.";
  }

  try {
    const payload = JSON.parse(text) as { detail?: unknown };

    if (typeof payload.detail === "string") {
      return payload.detail;
    }

    if (Array.isArray(payload.detail)) {
      return payload.detail.join(" ");
    }
  } catch {
    // Ignorar e devolver o texto cru.
  }

  return text;
}

export async function submitInvoice({
  qrPayload,
  tipo,
  observacoes,
  imageUri,
  imageName,
  imageType,
}: SubmitInvoiceInput): Promise<SubmitInvoiceResult> {
  if (!FATUREX_API_BASE_URL) {
    throw new Error("Definir EXPO_PUBLIC_FATUREX_API_BASE_URL.");
  }

  if (!FATUREX_API_KEY) {
    throw new Error("Definir EXPO_PUBLIC_FATUREX_API_KEY.");
  }

  const formData = new FormData();
  formData.append("qr_data", JSON.stringify(qrPayload));
  formData.append("tipo", tipo);
  formData.append("observacoes", observacoes?.trim() ?? "");
  formData.append(
    "file",
    {
      uri: imageUri,
      name: imageName ?? guessFileName(imageUri),
      type: imageType ?? "image/jpeg",
    } as never,
  );

  const response = await fetch(`${FATUREX_API_BASE_URL}/api/faturas/mobile`, {
    method: "POST",
    headers: {
      "X-API-Key": FATUREX_API_KEY,
    },
    body: formData,
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return JSON.parse(responseText) as SubmitInvoiceResult;
}
