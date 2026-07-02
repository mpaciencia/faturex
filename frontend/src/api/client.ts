import type { AtQrPayload, DocumentType } from "../utils/qrValidation";

export function getApiConfig() {
  const token = localStorage.getItem("faturex_token");
  const url = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");

  return { url, token };
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

export interface LoginResult {
  access_token: string;
  token_type: string;
  user_email: string;
  user_id: string;
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

export async function login(email: string, password: string): Promise<LoginResult> {
  const { url } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado no ficheiro .env.");
  }

  const response = await fetch(`${url}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return JSON.parse(responseText) as LoginResult;
}

export async function submitInvoice({
  qrPayload,
  tipo,
  observacoes,
  file,
}: SubmitInvoiceInput): Promise<SubmitInvoiceResult> {
  const { url, token } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado no ficheiro .env.");
  }

  if (!token) {
    throw new Error("Sessão não iniciada. Por favor, faça login.");
  }

  const formData = new FormData();
  formData.append("qr_data", JSON.stringify(qrPayload));
  formData.append("tipo", tipo);
  formData.append("observacoes", observacoes?.trim() ?? "");
  formData.append("file", file);

  const response = await fetch(`${url}/api/faturas/mobile`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
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
  const { url, token } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado no ficheiro .env.");
  }

  if (!token) {
    throw new Error("Sessão não iniciada. Por favor, faça login.");
  }

  const fetchUrl = `${url}/api/relatorios/excel?data_inicio=${startDate}&data_fim=${endDate}`;
  const response = await fetch(fetchUrl, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return response.blob();
}

export async function getZipExport(startDate: string, endDate: string): Promise<Blob> {
  const { url, token } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado no ficheiro .env.");
  }

  if (!token) {
    throw new Error("Sessão não iniciada. Por favor, faça login.");
  }

  const fetchUrl = `${url}/api/relatorios/zip?data_inicio=${startDate}&data_fim=${endDate}`;
  const response = await fetch(fetchUrl, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return response.blob();
}

// ---------------------------------------------------------------------------
// Submissão manual de PDF (Fluxo WebApp)
// ---------------------------------------------------------------------------

export interface SubmitPdfInput {
  file: File;
  observacoes?: string;
}

export async function submitPdfInvoice({
  file,
  observacoes,
}: SubmitPdfInput): Promise<SubmitInvoiceResult> {
  const { url, token } = getApiConfig();

  if (!url) {
    throw new Error("O URL do servidor API não está configurado no ficheiro .env.");
  }

  if (!token) {
    throw new Error("Sessão não iniciada. Por favor, faça login.");
  }

  const formData = new FormData();
  formData.append("file", file);
  if (observacoes?.trim()) {
    formData.append("observacoes", observacoes.trim());
  }

  const response = await fetch(`${url}/api/faturas/pdf`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
    body: formData,
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(parseBackendError(responseText) || `Erro HTTP ${response.status}`);
  }

  return JSON.parse(responseText) as SubmitInvoiceResult;
}

