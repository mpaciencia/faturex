export type DocumentType = "Despesa" | "Receita";

export interface AtQrPayload {
  atcud: string;
  nif_emissor: string;
  data_fatura: string;
  valor_total: string;
  imposto_total: string;
  raw_qr_string: string;
}

export class QrValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "QrValidationError";
  }
}

const REQUIRED_FIELDS = ["A", "F", "H", "N", "O"] as const;

function normalizeAmount(rawValue: string): string {
  const normalized = rawValue.trim().replace(",", ".");

  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) {
    throw new QrValidationError(`Valor monetário inválido: '${rawValue}'.`);
  }

  return normalized;
}

function normalizeDate(rawValue: string): string {
  if (!/^\d{8}$/.test(rawValue)) {
    throw new QrValidationError(`Campo 'F' inválido: '${rawValue}'. Esperado YYYYMMDD.`);
  }

  const year = Number(rawValue.slice(0, 4));
  const month = Number(rawValue.slice(4, 6)) - 1;
  const day = Number(rawValue.slice(6, 8));
  const parsedDate = new Date(Date.UTC(year, month, day));

  if (
    Number.isNaN(parsedDate.getTime()) ||
    parsedDate.getUTCFullYear() !== year ||
    parsedDate.getUTCMonth() !== month ||
    parsedDate.getUTCDate() !== day
  ) {
    throw new QrValidationError(`Campo 'F' contém uma data inválida: '${rawValue}'.`);
  }

  return rawValue;
}

function parseSegments(rawQr: string): Record<string, string> {
  const segments = rawQr
    .trim()
    .split("*")
    .map((segment) => segment.trim())
    .filter(Boolean);

  if (segments.length < REQUIRED_FIELDS.length) {
    throw new QrValidationError("QR Code AT incompleto.");
  }

  const parsed: Record<string, string> = {};

  for (const segment of segments) {
    const separatorIndex = segment.indexOf(":");

    if (separatorIndex <= 0) {
      continue;
    }

    const key = segment.slice(0, separatorIndex).trim();
    const value = segment.slice(separatorIndex + 1).trim();

    if (key) {
      parsed[key] = value;
    }
  }

  return parsed;
}

export function parseAtQrString(rawQr: string): AtQrPayload {
  if (!rawQr || !rawQr.trim()) {
    throw new QrValidationError("QR Code vazio.");
  }

  const parsed = parseSegments(rawQr);
  const missingFields = REQUIRED_FIELDS.filter((field) => !parsed[field]);

  if (missingFields.length > 0) {
    throw new QrValidationError(
      `QR Code AT inválido. Faltam os campos: ${missingFields.join(", ")}.`,
    );
  }

  if (!/^\d{9}$/.test(parsed.A)) {
    throw new QrValidationError(`Campo 'A' inválido: '${parsed.A}'. Esperado NIF com 9 dígitos.`);
  }

  normalizeDate(parsed.F);

  if (!parsed.H) {
    throw new QrValidationError("Campo 'H' (ATCUD) vazio.");
  }

  const valorTotal = normalizeAmount(parsed.O);
  const impostoTotal = normalizeAmount(parsed.N);

  return {
    atcud: parsed.H,
    nif_emissor: parsed.A,
    data_fatura: parsed.F,
    valor_total: valorTotal,
    imposto_total: impostoTotal,
    raw_qr_string: rawQr.trim(),
  };
}

export function buildQrDataJson(rawQr: string): string {
  return JSON.stringify(parseAtQrString(rawQr));
}
