import { useState } from "react";
import { Camera, FileSpreadsheet, LogOut } from "lucide-react";
import { Capture } from "./pages/Capture";
import { Reports } from "./pages/Reports";
import { Login } from "./pages/Login";

type Tab = "capture" | "reports";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("capture");
  const [token, setToken] = useState<string | null>(localStorage.getItem("faturex_token"));
  const [userEmail, setUserEmail] = useState<string | null>(localStorage.getItem("faturex_user_email"));

  const handleLoginSuccess = (newToken: string, email: string) => {
    localStorage.setItem("faturex_token", newToken);
    localStorage.setItem("faturex_user_email", email);
    setToken(newToken);
    setUserEmail(email);
    setActiveTab("capture");
  };

  const handleLogout = () => {
    localStorage.removeItem("faturex_token");
    localStorage.removeItem("faturex_user_email");
    setToken(null);
    setUserEmail(null);
  };

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <Camera size={20} />
          <span>Faturex</span>
        </div>

        {token && userEmail && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                background: "rgba(255, 255, 255, 0.05)",
                padding: "4px 10px",
                borderRadius: "12px",
                border: "1px solid var(--glass-border)",
                maxWidth: "150px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap"
              }}
              title={userEmail}
            >
              {userEmail}
            </div>
            <button
              onClick={handleLogout}
              style={{
                background: "none",
                border: "none",
                color: "var(--error)",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: 0.8,
                transition: "opacity 0.2s"
              }}
              title="Terminar Sessão"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </header>

      <main>
        {!token ? (
          <Login onLoginSuccess={handleLoginSuccess} />
        ) : (
          <>
            {activeTab === "capture" && <Capture />}
            {activeTab === "reports" && <Reports />}
          </>
        )}
      </main>

      {token && (
        <nav className="bottom-nav">
          <button
            className={`nav-item ${activeTab === "capture" ? "active" : ""}`}
            onClick={() => setActiveTab("capture")}
            style={{ width: "50%" }}
          >
            <Camera />
            <span>Digitalizar</span>
          </button>
          <button
            className={`nav-item ${activeTab === "reports" ? "active" : ""}`}
            onClick={() => setActiveTab("reports")}
            style={{ width: "50%" }}
          >
            <FileSpreadsheet />
            <span>Relatórios</span>
          </button>
        </nav>
      )}

      <div className="footer-text">
        Faturex Web v1.0.0
      </div>
    </div>
  );
}

export default App;
