import React, { useState, useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Camera, Upload, CheckCircle2, AlertTriangle, RefreshCw, FileText, Sparkles } from "lucide-react";
import { parseAtQrString, QrValidationError } from "../utils/qrValidation";
import type { AtQrPayload, DocumentType } from "../utils/qrValidation";
import { submitInvoice } from "../api/client";

type WorkflowStep = "scan_qr" | "capture_photo" | "confirm_details";

export function Capture() {
  const [step, setStep] = useState<WorkflowStep>("scan_qr");
  const [photoCaptureMode, setPhotoCaptureMode] = useState<"file" | "camera">("file");

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isScanningQr, setIsScanningQr] = useState(false);
  const [isCapturingPhoto, setIsCapturingPhoto] = useState(false);

  // Data States
  const [parsedData, setParsedData] = useState<AtQrPayload | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [tipo, setTipo] = useState<DocumentType>("Despesa");
  const [observacoes, setObservacoes] = useState("");
  const [successResult, setSuccessResult] = useState<{ id: string; categoria: string } | null>(null);

  const html5QrcodeRef = useRef<Html5Qrcode | null>(null);
  const cameraStreamRef = useRef<boolean>(false);

  // Cleanup camera streams on unmount
  useEffect(() => {
    return () => {
      stopCameraStream();
    };
  }, []);

  // Automatically start QR scanner on mount or when returning to scan step
  useEffect(() => {
    if (step === "scan_qr" && !successResult) {
      startQrScanner();
    }
    return () => {
      stopCameraStream();
    };
  }, [step, successResult]);

  const stopCameraStream = async () => {
    if (html5QrcodeRef.current && cameraStreamRef.current) {
      try {
        await html5QrcodeRef.current.stop();
      } catch (err) {
        console.error("Erro ao parar a câmara:", err);
      }
      cameraStreamRef.current = false;
    }
    setIsScanningQr(false);
    setIsCapturingPhoto(false);
  };

  // --- STEP 1: SCAN QR CODE ---

  const startQrScanner = async () => {
    setError(null);
    setSuccessResult(null);
    setParsedData(null);
    setSelectedFile(null);
    setPreviewUrl(null);

    // Ensure we stop any existing streams first
    await stopCameraStream();

    setIsScanningQr(true);
    // Let DOM update so the qr-reader container is present
    setTimeout(async () => {
      try {
        const html5Qrcode = new Html5Qrcode("qr-reader");
        html5QrcodeRef.current = html5Qrcode;

        await html5Qrcode.start(
          { facingMode: "environment" },
          {
            fps: 10,
            qrbox: (width, height) => {
              const size = Math.min(width, height) * 0.7;
              return { width: size, height: size };
            },
          },
          (qrText) => {
            handleQrDetected(qrText);
          },
          () => {
            // Silent scan failure for single frames
          }
        );
        cameraStreamRef.current = true;
      } catch (err: any) {
        console.error(err);
        setError("Não foi possível aceder à câmara em direto. Verifique as permissões de câmara do seu browser.");
        setIsScanningQr(false);
      }
    }, 150);
  };

  const handleQrDetected = async (qrText: string) => {
    setError(null);
    try {
      const payload = parseAtQrString(qrText);
      setParsedData(payload);

      // Stop scanner and move to next step
      await stopCameraStream();
      setStep("capture_photo");
    } catch (err: any) {
      if (err instanceof QrValidationError) {
        setError(`QR Code inválido: ${err.message}`);
      } else {
        setError("Erro ao ler dados do QR Code.");
      }
      stopCameraStream();
    }
  };

  // --- STEP 2: CAPTURE PHOTO ---

  const startPhotoCamera = async () => {
    setError(null);
    setSelectedFile(null);
    setPreviewUrl(null);

    setIsCapturingPhoto(true);
    setTimeout(async () => {
      try {
        const html5Qrcode = new Html5Qrcode("photo-reader");
        html5QrcodeRef.current = html5Qrcode;

        // Start display stream
        await html5Qrcode.start(
          { facingMode: "environment" },
          {
            fps: 15,
          },
          () => { }, // Empty callback since we only want the video view
          () => { }
        );
        cameraStreamRef.current = true;
      } catch (err: any) {
        console.error(err);
        setError("Não foi possível iniciar a câmara. Por favor use a opção de câmara nativa / galeria.");
        setIsCapturingPhoto(false);
      }
    }, 150);
  };

  const capturePhotoFromStream = async () => {
    setError(null);
    const videoElement = document.querySelector("#photo-reader video") as HTMLVideoElement;
    if (!videoElement) {
      setError("Câmara não disponível para capturar foto.");
      return;
    }

    setIsLoading(true);

    const canvas = document.createElement("canvas");
    canvas.width = videoElement.videoWidth || 1280;
    canvas.height = videoElement.videoHeight || 960;
    const ctx = canvas.getContext("2d");

    if (ctx) {
      ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        async (blob) => {
          if (blob) {
            const file = new File([blob], `fatura_capturada_${Date.now()}.jpg`, {
              type: "image/jpeg",
            });
            setSelectedFile(file);
            setPreviewUrl(URL.createObjectURL(file));

            // Stop stream and move to confirmation
            await stopCameraStream();
            setIsLoading(false);
            setStep("confirm_details");
          } else {
            setError("Erro ao gerar imagem a partir do stream da câmara.");
            setIsLoading(false);
          }
        },
        "image/jpeg",
        0.85
      );
    } else {
      setError("Erro ao aceder ao contexto de desenho da imagem.");
      setIsLoading(false);
    }
  };

  const handlePhotoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setStep("confirm_details");
  };

  // --- STEP 3: CONFIRM & SUBMIT ---

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parsedData || !selectedFile) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await submitInvoice({
        qrPayload: parsedData,
        tipo,
        observacoes,
        file: selectedFile,
      });
      setSuccessResult(result);
    } catch (err: any) {
      setError(err?.message || "Ocorreu um erro ao submeter a fatura.");
    } finally {
      setIsLoading(false);
    }
  };

  const resetAll = async () => {
    await stopCameraStream();
    setError(null);
    setSuccessResult(null);
    setParsedData(null);
    setSelectedFile(null);
    setPreviewUrl(null);
    setObservacoes("");
    setStep("scan_qr");
  };

  return (
    <div className="card">
      <div className="logo" style={{ justifyContent: "center", marginBottom: "20px" }}>
        <Sparkles size={24} />
        <span>Faturex Capture</span>
      </div>

      {/* Success View */}
      {successResult && (
        <div className="success-screen">
          <div className="success-icon-wrapper">
            <CheckCircle2 />
          </div>
          <h2>Fatura Registada!</h2>
          <p>Os dados fiscais e o comprovativo foram guardados com sucesso.</p>
          <div className="result-badge">
            Categoria: {successResult.categoria}
          </div>
          <button className="btn btn-primary" onClick={resetAll} style={{ marginTop: "24px" }}>
            Registar Nova Fatura
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="alert alert-error">
          <AlertTriangle />
          <div>
            <strong>Erro:</strong> {error}
          </div>
        </div>
      )}

      {/* Workflows */}
      {!successResult && (
        <>
          {/* STEP 1: SCAN QR CODE */}
          {step === "scan_qr" && (
            <div>
              <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "16px" }}>
                <span className="result-badge" style={{ background: "var(--primary)", color: "white" }}>1. Ler QR Code</span>
                <span className="result-badge" style={{ opacity: 0.4 }}>2. Tirar Foto</span>
                <span className="result-badge" style={{ opacity: 0.4 }}>3. Confirmar</span>
              </div>

              <h2 style={{ textAlign: "center", marginBottom: "8px" }}>Passo 1: Apontar ao QR Code</h2>
              <p style={{ textAlign: "center", marginBottom: "24px" }}>
                Posicione o QR Code da fatura portuguesa no centro do quadrado de digitalização.
              </p>

              {isScanningQr ? (
                <div className="scanner-container">
                  <div id="qr-reader"></div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0" }}>
                  <button className="btn btn-primary" onClick={startQrScanner}>
                    <Camera size={18} /> Iniciar Câmara
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: CAPTURE RECEIPT PHOTO */}
          {step === "capture_photo" && parsedData && (
            <div>
              <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "16px" }}>
                <span className="result-badge" style={{ background: "rgba(16, 185, 129, 0.2)", color: "var(--success)" }}>✓ QR Code Lido</span>
                <span className="result-badge" style={{ background: "var(--primary)", color: "white" }}>2. Tirar Foto</span>
                <span className="result-badge" style={{ opacity: 0.4 }}>3. Confirmar</span>
              </div>

              <h2 style={{ textAlign: "center", marginBottom: "8px" }}>Passo 2: Tirar Foto da Fatura</h2>
              <p style={{ textAlign: "center", marginBottom: "24px" }}>
                Agora tire uma fotografia nítida do documento de papel (comprovativo) para ser anexado e categorizado.
              </p>

              {!isCapturingPhoto && (
                <div className="tab-selector">
                  <button
                    className={`tab-btn ${photoCaptureMode === "file" ? "active" : ""}`}
                    onClick={() => setPhotoCaptureMode("file")}
                  >
                    <Upload size={16} style={{ display: "inline", marginRight: "6px", verticalAlign: "middle" }} />
                    Câmara do Telemóvel (Nativa) / Galeria
                  </button>
                  <button
                    className={`tab-btn ${photoCaptureMode === "camera" ? "active" : ""}`}
                    onClick={() => {
                      setPhotoCaptureMode("camera");
                      startPhotoCamera();
                    }}
                  >
                    <Camera size={16} style={{ display: "inline", marginRight: "6px", verticalAlign: "middle" }} />
                    Câmara do Browser
                  </button>
                </div>
              )}

              {photoCaptureMode === "file" && !isLoading && (
                <div>
                  <label htmlFor="photo-file-input" className="file-upload-zone">
                    <Camera />
                    <div>
                      <span style={{ fontWeight: 600, color: "var(--primary)" }}>Abrir Câmara do Telemóvel</span>
                    </div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                      Tire uma fotografia do talão completo.
                    </span>
                  </label>
                  <input
                    id="photo-file-input"
                    type="file"
                    accept="image/*"
                    capture="environment"
                    style={{ display: "none" }}
                    onChange={handlePhotoFileChange}
                    disabled={isLoading}
                  />
                </div>
              )}

              {isCapturingPhoto && (
                <div className="scanner-container">
                  <div id="photo-reader" style={{ borderStyle: "solid" }}></div>

                  <div style={{ display: "flex", gap: "12px", width: "100%" }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        stopCameraStream();
                        setPhotoCaptureMode("file");
                      }}
                      style={{ flex: 1 }}
                    >
                      Voltar
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={capturePhotoFromStream}
                      style={{ flex: 2 }}
                    >
                      <Camera size={18} /> Tirar Foto
                    </button>
                  </div>
                </div>
              )}

              {isLoading && (
                <div style={{ textAlign: "center", padding: "40px 0" }}>
                  <div className="spinner" style={{ marginBottom: "16px" }}></div>
                  <p>A capturar imagem...</p>
                </div>
              )}

              <button
                className="btn btn-secondary"
                onClick={resetAll}
                style={{ marginTop: "24px" }}
              >
                Reiniciar Fluxo
              </button>
            </div>
          )}

          {/* STEP 3: CONFIRM DETAILS & SUBMIT */}
          {step === "confirm_details" && parsedData && selectedFile && (
            <form onSubmit={handleSubmit}>
              <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "16px" }}>
                <span className="result-badge" style={{ background: "rgba(16, 185, 129, 0.2)", color: "var(--success)" }}>✓ QR Code</span>
                <span className="result-badge" style={{ background: "rgba(16, 185, 129, 0.2)", color: "var(--success)" }}>✓ Foto</span>
                <span className="result-badge" style={{ background: "var(--primary)", color: "white" }}>3. Confirmar</span>
              </div>

              <h2>Passo 3: Confirmar e Enviar</h2>
              <p style={{ marginBottom: "20px" }}>
                Valide os dados lidos e submeta a fatura para categorização automática.
              </p>

              {previewUrl && (
                <div className="image-preview-container">
                  <img src={previewUrl} alt="Comprovativo capturado" className="image-preview" />
                </div>
              )}

              <div className="form-group">
                <label>Tipo de Documento</label>
                <div className="tab-selector" style={{ marginBottom: 0 }}>
                  <button
                    type="button"
                    className={`tab-btn ${tipo === "Despesa" ? "active" : ""}`}
                    onClick={() => setTipo("Despesa")}
                  >
                    Despesa
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${tipo === "Receita" ? "active" : ""}`}
                    onClick={() => setTipo("Receita")}
                  >
                    Receita
                  </button>
                </div>
              </div>

              <div className="summary-grid">
                <div className="summary-item">
                  <span className="summary-label">NIF Emissor</span>
                  <span className="summary-value">{parsedData.nif_emissor}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Data</span>
                  <span className="summary-value">
                    {parsedData.data_fatura.replace(
                      /(\d{4})(\d{2})(\d{2})/,
                      "$1-$2-$3"
                    )}
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Valor Total</span>
                  <span className="summary-value">{parsedData.valor_total} €</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">IVA</span>
                  <span className="summary-value">{parsedData.imposto_total} €</span>
                </div>
                <div className="summary-item full-width">
                  <span className="summary-label">ATCUD</span>
                  <span className="summary-value" style={{ fontSize: "0.85rem", wordBreak: "break-all" }}>
                    {parsedData.atcud}
                  </span>
                </div>
              </div>

              <div className="form-group" style={{ marginTop: "20px" }}>
                <label htmlFor="observacoes">Observações (opcional)</label>
                <textarea
                  id="observacoes"
                  className="form-control"
                  rows={3}
                  placeholder="Ex: Almoço com cliente X, Material para obra Y..."
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={resetAll}
                  disabled={isLoading}
                  style={{ flex: 1 }}
                >
                  <RefreshCw size={16} /> Reiniciar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isLoading}
                  style={{ flex: 2 }}
                >
                  {isLoading ? (
                    <>
                      <div className="spinner" style={{ width: "16px", height: "16px" }}></div> A enviar...
                    </>
                  ) : (
                    <>
                      <FileText size={16} /> Submeter Fatura
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </div>
  );
}
