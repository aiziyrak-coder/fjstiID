import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";

export function LoginPage() {
  const { t } = useTranslation();
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>{t("brand")}</h1>
        <p>{t("brandSub")} — Farg'ona JSTI</p>
        <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
          <label>
            {t("email")}
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </label>
          <label>
            {t("password")}
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="btn accent" style={{ width: "100%", marginTop: "1rem" }} disabled={busy}>
          {t("login")}
        </button>
      </form>
    </div>
  );
}
