import { useState, useEffect } from "react";
import { Camera, FileSpreadsheet, Settings as SettingsIcon, AlertCircle } from "lucide-react";
import { getApiConfig } from "./api/client";
import { Capture } from "./pages/Capture";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";

type Tab = "capture" | "reports" | "settings";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("capture");
  const [isConfigured, setIsConfigured] = useState(true);

  // Check config on load and tab change
  const checkConfig = () => {
    const config = getApiConfig();
    const configured = !!(config.url && config.key);
    setIsConfigured(configured);
    return configured;
  };

  useEffect(() => {
    const configured = checkConfig();
    if (!configured) {
      setActiveTab("settings");
    }
  }, []);

  // Check config whenever switching tabs to update status
  const handleTabChange = (tab: Tab) => {
    checkConfig();
    setActiveTab(tab);
  };

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <Camera size={20} />
          <span>Faturex</span>
        </div>

        {!isConfigured && (
          <div
            onClick={() => setActiveTab("settings")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.8rem",
              color: "var(--error)",
              cursor: "pointer",
              background: "rgba(244, 63, 94, 0.1)",
              padding: "4px 8px",
              borderRadius: "12px",
              border: "1px solid rgba(244, 63, 94, 0.2)"
            }}
          >
            <AlertCircle size={14} />
            <span>Não Configurado</span>
          </div>
        )}
      </header>

      <main>
        {activeTab === "capture" && <Capture />}
        {activeTab === "reports" && <Reports />}
        {activeTab === "settings" && <Settings />}
      </main>

      <nav className="bottom-nav">
        <button
          className={`nav-item ${activeTab === "capture" ? "active" : ""}`}
          onClick={() => handleTabChange("capture")}
        >
          <Camera />
          <span>Digitalizar</span>
        </button>
        <button
          className={`nav-item ${activeTab === "reports" ? "active" : ""}`}
          onClick={() => handleTabChange("reports")}
        >
          <FileSpreadsheet />
          <span>Relatórios</span>
        </button>
        <button
          className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => handleTabChange("settings")}
        >
          <SettingsIcon />
          <span>Definições</span>
        </button>
      </nav>

      <div className="footer-text">
        Faturex Web v1.0.0
      </div>
    </div>
  );
}

export default App;
