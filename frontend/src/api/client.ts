import type { AtQrPayload, DocumentType } from "../utils/qrValidation";

export function getApiConfig() {
  const localUrl = localStorage.getItem("faturex_api_url");
  const localKey = localStorage.getItem("faturex_api_key");
  
  const url = (localUrl || import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");
  const key = (localKey || import.meta.env.VITE_API_KEY || "").trim();

  return { url, key };
}

export interface SubmitInvoiceInput {
  qrPayload: AtQrPayload;
  tipo: DocumentType;
  observacoes?: string;
  file: File;
}

export interface SubmitInvoiceResult {
  id: string;
  categoria: string;
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
    // Ignore and return raw text
  }

  return text;
}

export async function submitInvoice({
  qrPayload,
  tipo,
  observacoes,
  file,
}: SubmitInvoiceInput): Promise<SubmitInvoiceResult> {
  const { url, key } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado. Aceda às Definições.");
  }

  if (!key) {
    throw new Error("A chave de API não está configurada. Aceda às Definições.");
  }

  const formData = new FormData();
  formData.append("qr_data", JSON.stringify(qrPayload));
  formData.append("tipo", tipo);
  formData.append("observacoes", observacoes?.trim() ?? "");
  formData.append("file", file);

  const response = await fetch(`${url}/api/faturas/mobile`, {
    method: "POST",
    headers: {
      "X-API-Key": key,
    },
    body: formData,
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return JSON.parse(responseText) as SubmitInvoiceResult;
}

export async function getExcelReport(startDate: string, endDate: string): Promise<Blob> {
  const { url, key } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado. Aceda às Definições.");
  }

  if (!key) {
    throw new Error("A chave de API não está configurada. Aceda às Definições.");
  }

  const fetchUrl = `${url}/api/relatorios/excel?data_inicio=${startDate}&data_fim=${endDate}`;
  const response = await fetch(fetchUrl, {
    method: "GET",
    headers: {
      "X-API-Key": key,
    },
  });

  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return response.blob();
}

export async function getZipExport(startDate: string, endDate: string): Promise<Blob> {
  const { url, key } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado. Aceda às Definições.");
  }

  if (!key) {
    throw new Error("A chave de API não está configurada. Aceda às Definições.");
  }

  const fetchUrl = `${url}/api/relatorios/zip?data_inicio=${startDate}&data_fim=${endDate}`;
  const response = await fetch(fetchUrl, {
    method: "GET",
    headers: {
      "X-API-Key": key,
    },
  });

  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return response.blob();
}

