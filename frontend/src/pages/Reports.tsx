import { useState } from "react";
import { FileSpreadsheet, FileArchive, Calendar, AlertTriangle } from "lucide-react";
import { getExcelReport, getZipExport } from "../api/client";

export function Reports() {
  const today = new Date();
  
  // Default dates (current quarter)
  const getQuarterDates = (offset = 0) => {
    const date = new Date();
    const currentMonth = date.getMonth();
    const currentQuarter = Math.floor(currentMonth / 3) + offset;
    
    const startMonth = currentQuarter * 3;
    const startYear = date.getFullYear() + Math.floor(startMonth / 12);
    const correctedStartMonth = (startMonth + 12) % 12;
    
    const startDate = new Date(startYear, correctedStartMonth, 1);
    const endDate = new Date(startYear, correctedStartMonth + 3, 0); // last day of quarter
    
    const formatDate = (d: Date) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };
    
    return {
      start: formatDate(startDate),
      end: formatDate(endDate),
    };
  };

  const currentQuarter = getQuarterDates(0);
  
  const [startDate, setStartDate] = useState(currentQuarter.start);
  const [endDate, setEndDate] = useState(currentQuarter.end);
  const [activePeriod, setActivePeriod] = useState<"q-curr" | "q-prev" | "y-curr" | "custom">("q-curr");
  
  const [isLoadingExcel, setIsLoadingExcel] = useState(false);
  const [isLoadingZip, setIsLoadingZip] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setPeriod = (period: "q-curr" | "q-prev" | "y-curr") => {
    setActivePeriod(period);
    setError(null);
    if (period === "q-curr") {
      const dates = getQuarterDates(0);
      setStartDate(dates.start);
      setEndDate(dates.end);
    } else if (period === "q-prev") {
      const dates = getQuarterDates(-1);
      setStartDate(dates.start);
      setEndDate(dates.end);
    } else if (period === "y-curr") {
      const year = today.getFullYear();
      setStartDate(`${year}-01-01`);
      setEndDate(`${year}-12-31`);
    }
  };

  const handleExcelDownload = async () => {
    if (!startDate || !endDate) {
      setError("Por favor selecione a data de início e de fim.");
      return;
    }

    setIsLoadingExcel(true);
    setError(null);

    try {
      const blob = await getExcelReport(startDate, endDate);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      const cleanStart = startDate.replace(/-/g, "");
      const cleanEnd = endDate.replace(/-/g, "");
      a.download = `relatorio_${cleanStart}_${cleanEnd}.xlsx`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message || "Erro ao descarregar relatório Excel.");
    } finally {
      setIsLoadingExcel(false);
    }
  };

  const handleZipDownload = async () => {
    if (!startDate || !endDate) {
      setError("Por favor selecione a data de início e de fim.");
      return;
    }

    setIsLoadingZip(true);
    setError(null);

    try {
      const blob = await getZipExport(startDate, endDate);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      const cleanStart = startDate.replace(/-/g, "");
      const cleanEnd = endDate.replace(/-/g, "");
      a.download = `faturas_${cleanStart}_${cleanEnd}.zip`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message || "Erro ao descarregar exportação ZIP.");
    } finally {
      setIsLoadingZip(false);
    }
  };

  return (
    <div className="card">
      <div className="logo" style={{ justifyContent: "center", marginBottom: "20px" }}>
        <Calendar size={24} />
        <span>Exportar Faturas</span>
      </div>

      <h2 style={{ textAlign: "center", marginBottom: "8px" }}>Gerar Relatórios</h2>
      <p style={{ textAlign: "center", marginBottom: "24px" }}>
        Selecione o intervalo de datas para gerar a folha de cálculo Excel para a contabilidade ou descarregar os comprovativos em formato ZIP.
      </p>

      {error && (
        <div className="alert alert-error">
          <AlertTriangle />
          <div>
            <strong>Erro:</strong> {error}
          </div>
        </div>
      )}

      {/* Quick Selectors */}
      <div className="quick-periods">
        <button
          className={`quick-period-btn ${activePeriod === "q-curr" ? "active" : ""}`}
          onClick={() => setPeriod("q-curr")}
        >
          Este Trimestre
        </button>
        <button
          className={`quick-period-btn ${activePeriod === "q-prev" ? "active" : ""}`}
          onClick={() => setPeriod("q-prev")}
        >
          Trimestre Anterior
        </button>
        <button
          className={`quick-period-btn ${activePeriod === "y-curr" ? "active" : ""}`}
          onClick={() => setPeriod("y-curr")}
        >
          Este Ano
        </button>
      </div>

      {/* Date Pickers */}
      <div className="date-grid">
        <div className="form-group">
          <label htmlFor="start-date">Data de Início</label>
          <input
            type="date"
            id="start-date"
            className="form-control"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setActivePeriod("custom");
            }}
          />
        </div>
        <div className="form-group">
          <label htmlFor="end-date">Data de Fim</label>
          <input
            type="date"
            id="end-date"
            className="form-control"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setActivePeriod("custom");
            }}
          />
        </div>
      </div>

      {/* Download Buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}>
        <button
          className="btn btn-primary"
          onClick={handleExcelDownload}
          disabled={isLoadingExcel || isLoadingZip}
          style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 4px 15px rgba(16, 185, 129, 0.3)" }}
        >
          {isLoadingExcel ? (
            <>
              <div className="spinner" style={{ width: "16px", height: "16px" }}></div> A gerar Excel...
            </>
          ) : (
            <>
              <FileSpreadsheet size={18} /> Descarregar Excel (.xlsx)
            </>
          )}
        </button>

        <button
          className="btn btn-primary"
          onClick={handleZipDownload}
          disabled={isLoadingExcel || isLoadingZip}
        >
          {isLoadingZip ? (
            <>
              <div className="spinner" style={{ width: "16px", height: "16px" }}></div> A compactar documentos...
            </>
          ) : (
            <>
              <FileArchive size={18} /> Descarregar Anexos (.zip)
            </>
          )}
        </button>
      </div>

      <div style={{ marginTop: "24px", padding: "12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "10px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
        <strong>Nota Fiscal:</strong> O ficheiro Excel gerado conterá as folhas "Despesas" e "Receitas" organizadas com fórmulas de totais e subtotais por categoria de forma automática.
      </div>
    </div>
  );
}
