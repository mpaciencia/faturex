import { useState, useEffect } from "react";
import { Settings as SettingsIcon, Save, RotateCcw, AlertCircle, ShieldCheck } from "lucide-react";
import { getApiConfig } from "../api/client";

export function Settings() {
  const [apiUrl, setApiUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isSaved, setIsSaved] = useState(false);
  
  // Environment defaults for reference
  const envUrl = import.meta.env.VITE_API_URL || "";
  const envKey = import.meta.env.VITE_API_KEY || "";

  useEffect(() => {
    // Load local storage values or fallback to env
    const localUrl = localStorage.getItem("faturex_api_url") || "";
    const localKey = localStorage.getItem("faturex_api_key") || "";
    
    setApiUrl(localUrl);
    setApiKey(localKey);
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (apiUrl.trim()) {
      localStorage.setItem("faturex_api_url", apiUrl.trim());
    } else {
      localStorage.removeItem("faturex_api_url");
    }

    if (apiKey.trim()) {
      localStorage.setItem("faturex_api_key", apiKey.trim());
    } else {
      localStorage.removeItem("faturex_api_key");
    }

    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  const handleReset = () => {
    localStorage.removeItem("faturex_api_url");
    localStorage.removeItem("faturex_api_key");
    setApiUrl("");
    setApiKey("");
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  const activeConfig = getApiConfig();
  const isConfigured = activeConfig.url && activeConfig.key;

  return (
    <div className="card">
      <div className="logo" style={{ justifyContent: "center", marginBottom: "20px" }}>
        <SettingsIcon size={24} />
        <span>Definições</span>
      </div>

      <h2 style={{ textAlign: "center", marginBottom: "8px" }}>Configuração de API</h2>
      <p style={{ textAlign: "center", marginBottom: "24px" }}>
        Configure a ligação ao backend do Faturex. Os valores inseridos aqui serão guardados no seu browser.
      </p>

      {isSaved && (
        <div className="alert alert-success">
          <ShieldCheck />
          <div>Definições gravadas com sucesso!</div>
        </div>
      )}

      {!isConfigured && (
        <div className="alert alert-error" style={{ marginBottom: "24px" }}>
          <AlertCircle />
          <div>
            <strong>Atenção:</strong> A aplicação não está configurada. Tem de definir o URL do servidor e a chave API para poder digitalizar faturas e obter relatórios.
          </div>
        </div>
      )}

      {isConfigured && !localStorage.getItem("faturex_api_url") && !localStorage.getItem("faturex_api_key") && (
        <div className="settings-warning" style={{ background: "rgba(16, 185, 129, 0.1)", borderColor: "rgba(16, 185, 129, 0.2)", color: "#a7f3d0" }}>
          <ShieldCheck size={20} style={{ color: "var(--success)" }} />
          <div>
            A utilizar as configurações padrão do sistema (.env de build).
          </div>
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="form-group">
          <label htmlFor="api-url">URL do Servidor API</label>
          <input
            type="url"
            id="api-url"
            className="form-control"
            placeholder="http://localhost:8000"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
          />
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "4px", display: "block" }}>
            {envUrl ? `Padrão do sistema: ${envUrl}` : "Nenhum padrão configurado no build."}
          </span>
        </div>

        <div className="form-group">
          <label htmlFor="api-key">Chave de API (X-API-Key)</label>
          <input
            type="password"
            id="api-key"
            className="form-control"
            placeholder="Introduza a chave de segurança..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "4px", display: "block" }}>
            {envKey ? "Padrão do sistema: Chave configurada." : "Nenhuma chave padrão configurada no build."}
          </span>
        </div>

        <div style={{ display: "flex", gap: "12px", marginTop: "28px" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleReset}
            style={{ flex: 1 }}
          >
            <RotateCcw size={16} /> Limpar
          </button>
          
          <button
            type="submit"
            className="btn btn-primary"
            style={{ flex: 2 }}
          >
            <Save size={16} /> Gravar Definições
          </button>
        </div>
      </form>
      
      <div style={{ marginTop: "32px", borderTop: "1px solid var(--glass-border)", paddingTop: "20px" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "8px" }}>
          Configuração Ativa:
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <div><strong>URL:</strong> {activeConfig.url || <span style={{ color: "var(--error)" }}>Não configurado</span>}</div>
          <div><strong>Chave:</strong> {activeConfig.key ? "••••••••••••••••" : <span style={{ color: "var(--error)" }}>Não configurado</span>}</div>
        </div>
      </div>
    </div>
  );
}
