import React, { useState, useEffect, useRef, useCallback } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Camera, Upload, CheckCircle2, AlertTriangle, RefreshCw, FileText, Sparkles, FileUp, X, Lock } from "lucide-react";
import { parseAtQrString, QrValidationError } from "../utils/qrValidation";
import type { AtQrPayload, DocumentType } from "../utils/qrValidation";
import { submitInvoice, submitPdfInvoice } from "../api/client";

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

  // PDF Upload States
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfObservacoes, setPdfObservacoes] = useState("");
  const [pdfIsLoading, setPdfIsLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pdfIsDragging, setPdfIsDragging] = useState(false);
  const [pdfToast, setPdfToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const pdfInputRef = useRef<HTMLInputElement>(null);

  // Camera selection (avoids virtual/continuity cameras that send split/combined feeds)
  const [availableCameras, setAvailableCameras] = useState<{ id: string; label: string }[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);

  const html5QrcodeRef = useRef<Html5Qrcode | null>(null);
  const cameraStreamRef = useRef<boolean>(false);
  const isMounted = useRef<boolean>(true);
  const timeoutsRef = useRef<any[]>([]);

  // Regex to flag virtual / continuity / screen-sharing style cameras whose
  // feed can come pre-combined (e.g. Apple Continuity Camera "Desk View",
  // OBS Virtual Camera, Snap Camera, etc.)
  const VIRTUAL_CAMERA_PATTERN = /iphone|ipad|continuity|desk view|virtual|obs|snap camera|droidcam|epoccam/i;

  const resolveCameraId = async (overrideId?: string): Promise<string | null> => {
    try {
      const cameras = await Html5Qrcode.getCameras();
      setAvailableCameras(cameras);

      if (!cameras || cameras.length === 0) return null;

      const desiredId = overrideId ?? selectedCameraId;

      // If a specific camera was requested (manual pick or already chosen), respect it.
      if (desiredId && cameras.some((c) => c.id === desiredId)) {
        setSelectedCameraId(desiredId);
        return desiredId;
      }

      // Prefer rear/back cameras, excluding virtual ones
      const backCamera = cameras.find((c) => 
        /back|rear|environment|traseira/i.test(c.label) && !VIRTUAL_CAMERA_PATTERN.test(c.label)
      );
      // Fallback to any non-virtual camera
      const preferred = backCamera ?? cameras.find((c) => !VIRTUAL_CAMERA_PATTERN.test(c.label));
      const chosen = preferred ?? cameras[0];
      setSelectedCameraId(chosen.id);
      return chosen.id;
    } catch (err) {
      console.error("Erro ao listar câmaras:", err);
      return null;
    }
  };

  // Cleanup camera streams on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
      timeoutsRef.current.forEach(clearTimeout);
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
        html5QrcodeRef.current.clear();
        html5QrcodeRef.current = null;
      } catch (err) {
        console.error("Erro ao parar a câmara:", err);
      }
      cameraStreamRef.current = false;
    }
    if (isMounted.current) {
      setIsScanningQr(false);
      setIsCapturingPhoto(false);
    }
  };

  // --- STEP 1: SCAN QR CODE ---

  const startQrScanner = async (cameraOverrideId?: string | React.MouseEvent) => {
    const validOverrideId = typeof cameraOverrideId === "string" ? cameraOverrideId : undefined;
    setError(null);
    setSuccessResult(null);
    setParsedData(null);
    setSelectedFile(null);
    setPreviewUrl(null);

    // Ensure we stop any existing streams first
    await stopCameraStream();

    setIsScanningQr(true);
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
    // Let DOM update so the qr-reader container is present
    const timeoutId = setTimeout(async () => {
      try {
        const html5Qrcode = new Html5Qrcode("qr-reader");
        html5QrcodeRef.current = html5Qrcode;

        const cameraId = await resolveCameraId(validOverrideId);
        const cameraConfig: any = cameraId ?? { facingMode: "environment" };

        await html5Qrcode.start(
          cameraConfig,
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
    timeoutsRef.current.push(timeoutId);
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
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
    const timeoutId = setTimeout(async () => {
      try {
        const html5Qrcode = new Html5Qrcode("photo-reader");
        html5QrcodeRef.current = html5Qrcode;

        const cameraId = await resolveCameraId();
        const cameraConfig: any = cameraId ?? { facingMode: "environment" };

        // Start display stream
        await html5Qrcode.start(
          cameraConfig,
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
    timeoutsRef.current.push(timeoutId);
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
          if (!isMounted.current) return;
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

  // --- PDF Upload Handlers ---

  const showPdfToast = (type: "success" | "error", message: string) => {
    setPdfToast({ type, message });
    setTimeout(() => setPdfToast(null), 4000);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handlePdfSelect = (file: File) => {
    if (file.type !== "application/pdf") {
      setPdfError("Apenas ficheiros PDF são aceites.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setPdfError("O ficheiro excede o limite de 20 MB.");
      return;
    }
    setPdfError(null);
    setPdfFile(file);
  };

  const handlePdfFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handlePdfSelect(file);
    // Reset input so the same file can be re-selected
    e.target.value = "";
  };

  const handlePdfDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPdfIsDragging(true);
  }, []);

  const handlePdfDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPdfIsDragging(false);
  }, []);

  const handlePdfDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPdfIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handlePdfSelect(file);
  }, []);

  const handlePdfSubmit = async () => {
    if (!pdfFile) return;
    setPdfIsLoading(true);
    setPdfError(null);

    try {
      const result = await submitPdfInvoice({
        file: pdfFile,
        observacoes: pdfObservacoes,
      });
      showPdfToast("success", `Fatura registada! Categoria: ${result.categoria}`);
      setPdfFile(null);
      setPdfObservacoes("");
      if (pdfInputRef.current) pdfInputRef.current.value = "";
    } catch (err: any) {
      const msg = err?.message || "Erro ao submeter o PDF.";
      setPdfError(msg);
      showPdfToast("error", msg);
    } finally {
      setPdfIsLoading(false);
    }
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
                  {availableCameras.length > 1 && (
                    <div className="form-group" style={{ width: "100%" }}>
                      <label htmlFor="camera-select-qr">Câmara</label>
                      <select
                        id="camera-select-qr"
                        className="form-control"
                        value={selectedCameraId ?? ""}
                        onChange={async (e) => {
                          const newId = e.target.value;
                          await stopCameraStream();
                          startQrScanner(newId);
                        }}
                      >
                        {availableCameras.map((cam) => (
                          <option key={cam.id} value={cam.id}>
                            {cam.label || cam.id}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
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

      {/* ============================================================ */}
      {/* PDF UPLOAD SECTION                                           */}
      {/* ============================================================ */}
      <div className="section-divider">
        <span>Ou submeter PDF</span>
      </div>

      <div className="card">
        <div className="logo" style={{ justifyContent: "center", marginBottom: "16px" }}>
          <FileUp size={22} />
          <span>Submeter Fatura PDF</span>
        </div>
        <p style={{ textAlign: "center", marginBottom: "20px" }}>
          Arraste ou selecione um ficheiro PDF de uma fatura para processar automaticamente.
        </p>

        {/* Drag & Drop Zone */}
        {!pdfFile && (
          <label
            htmlFor="pdf-file-input"
            className={`pdf-upload-zone ${pdfIsDragging ? "pdf-drop-active" : ""}`}
            onDragOver={handlePdfDragOver}
            onDragLeave={handlePdfDragLeave}
            onDrop={handlePdfDrop}
          >
            <FileUp />
            <div>
              <span style={{ fontWeight: 600, color: "var(--accent)" }}>Selecionar ou arrastar PDF</span>
            </div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Ficheiros PDF até 20 MB
            </span>
          </label>
        )}
        <input
          ref={pdfInputRef}
          id="pdf-file-input"
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={handlePdfFileChange}
          disabled={pdfIsLoading}
        />

        {/* File Preview */}
        {pdfFile && (
          <div className="pdf-file-preview">
            <FileText />
            <div className="pdf-file-info">
              <div className="pdf-file-name">{pdfFile.name}</div>
              <div className="pdf-file-size">{formatFileSize(pdfFile.size)}</div>
            </div>
            <button
              className="pdf-file-remove"
              onClick={() => { setPdfFile(null); setPdfError(null); }}
              disabled={pdfIsLoading}
              title="Remover ficheiro"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Error */}
        {pdfError && (
          <div className="alert alert-error" style={{ marginTop: "16px" }}>
            <AlertTriangle />
            <div>
              <strong>Erro:</strong> {pdfError}
            </div>
          </div>
        )}

        {pdfFile && (
          <>
            {/* Tipo de Documento (locked) */}
            <div className="form-group" style={{ marginTop: "20px" }}>
              <label>Tipo de Documento</label>
              <div className="tipo-locked-badge">
                <Lock size={14} />
                Despesa
              </div>
            </div>

            {/* Observações */}
            <div className="form-group">
              <label htmlFor="pdf-observacoes">Observações (opcional)</label>
              <textarea
                id="pdf-observacoes"
                className="form-control"
                rows={3}
                placeholder="Ex: Fatura da EDP, Material para obra Y..."
                value={pdfObservacoes}
                onChange={(e) => setPdfObservacoes(e.target.value)}
                disabled={pdfIsLoading}
              />
            </div>

            {/* Submit Button */}
            <button
              className="btn btn-primary"
              onClick={handlePdfSubmit}
              disabled={pdfIsLoading}
              style={{ marginTop: "8px" }}
            >
              {pdfIsLoading ? (
                <>
                  <div className="spinner" style={{ width: "16px", height: "16px" }}></div> A processar...
                </>
              ) : (
                <>
                  <FileUp size={16} /> Submeter PDF
                </>
              )}
            </button>
          </>
        )}
      </div>

      {/* Toast Notification */}
      {pdfToast && (
        <div className={`toast toast-${pdfToast.type}`}>
          {pdfToast.type === "success" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          {pdfToast.message}
        </div>
      )}
    </div>
  );
}