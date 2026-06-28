type SubmitInvoiceArgs = {
  baseUrl: string;
  apiKey: string;
  qrData: string;
  tipo: "Despesa" | "Receita";
  fileUri: string;
};

type SubmitInvoiceResponse = {
  id: string;
  categoria: string;
};

export async function submitInvoiceMobile({ baseUrl, apiKey, qrData, tipo, fileUri }: SubmitInvoiceArgs): Promise<SubmitInvoiceResponse> {
  const formData = new FormData();

  formData.append("qr_data", qrData);
  formData.append("tipo", tipo);
  formData.append("file", {
    uri: fileUri,
    name: fileUri.split("/").pop() ?? "invoice.jpg",
    type: fileUri.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg",
  } as unknown as Blob);

  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/faturas/mobile`, {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
    },
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = data?.detail ?? data?.message ?? `Erro HTTP ${response.status}`;
    throw new Error(typeof message === "string" ? message : "Erro ao enviar a fatura.");
  }

  return data as SubmitInvoiceResponse;
}
