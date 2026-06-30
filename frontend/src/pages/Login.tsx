import React, { useState } from "react";
import { Lock, Mail, Eye, EyeOff, Sparkles, AlertCircle } from "lucide-react";
import { login } from "../api/client";

interface LoginProps {
  onLoginSuccess: (token: string, email: string) => void;
}

export function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await login(email.trim(), password);
      onLoginSuccess(result.access_token, result.user_email);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Ocorreu um erro ao tentar iniciar sessão. Verifique se o servidor está ativo.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: "420px", margin: "60px auto 0 auto" }}>
      <div className="logo" style={{ justifyContent: "center", marginBottom: "20px" }}>
        <Sparkles size={28} />
        <span>Faturex</span>
      </div>

      <h2 style={{ textAlign: "center", marginBottom: "8px" }}>Iniciar Sessão</h2>
      <p style={{ textAlign: "center", marginBottom: "28px" }}>
        Introduza as suas credenciais para gerir e digitalizar as suas faturas.
      </p>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: "20px" }}>
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <div style={{ position: "relative" }}>
            <Mail
              size={18}
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-secondary)",
              }}
            />
            <input
              type="email"
              id="email"
              className="form-control"
              placeholder="exemplo@faturex.pt"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{ paddingLeft: "44px" }}
            />
          </div>
        </div>

        <div className="form-group" style={{ marginTop: "18px" }}>
          <label htmlFor="password">Palavra-passe</label>
          <div style={{ position: "relative" }}>
            <Lock
              size={18}
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-secondary)",
              }}
            />
            <input
              type={showPassword ? "text" : "password"}
              id="password"
              className="form-control"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ paddingLeft: "44px", paddingRight: "44px" }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: "absolute",
                right: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                color: "var(--text-secondary)",
                cursor: "pointer",
                padding: 0,
                display: "flex",
                alignItems: "center",
              }}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
          style={{ marginTop: "32px", height: "50px" }}
        >
          {isLoading ? "A processar..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
