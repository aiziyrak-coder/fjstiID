import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export function LogsPage() {
  const [tab, setTab] = useState<"access" | "audit">("access");
  const [access, setAccess] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [method, setMethod] = useState("");
  const [success, setSuccess] = useState("");
  const [q, setQ] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    setError("");
    if (tab === "access") {
      api
        .accessLogs({
          page,
          page_size: 50,
          method: method || undefined,
          success: success === "" ? undefined : success === "1",
          q: q || undefined,
        })
        .then((r) => {
          setAccess(r.items);
          setTotal(r.total);
        })
        .catch((e) => setError(e.message));
    } else {
      api
        .auditLogs({ page, page_size: 50 })
        .then((r) => {
          setAudit(r.items);
          setTotal(r.total);
        })
        .catch((e) => setError(e.message));
    }
  };

  useEffect(() => {
    load();
  }, [tab, page, method, success]);

  return (
    <div>
      <h2>Jurnallar</h2>
      <p className="muted">Kirishlar va admin amallari — filtr + sahifalash</p>
      {error && <p className="error">{error}</p>}
      <div className="tabs">
        <button className={`tab${tab === "access" ? " active" : ""}`} onClick={() => { setTab("access"); setPage(1); }}>Kirishlar</button>
        <button className={`tab${tab === "audit" ? " active" : ""}`} onClick={() => { setTab("audit"); setPage(1); }}>Audit</button>
      </div>

      {tab === "access" && (
        <div className="panel filters">
          <input placeholder="Qidirish..." value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={method} onChange={(e) => { setMethod(e.target.value); setPage(1); }}>
            <option value="">Metod</option>
            <option value="face">face</option>
            <option value="password">password</option>
            <option value="qr">qr</option>
          </select>
          <select value={success} onChange={(e) => { setSuccess(e.target.value); setPage(1); }}>
            <option value="">Natija</option>
            <option value="1">OK</option>
            <option value="0">Xato</option>
          </select>
          <button className="btn secondary" onClick={() => { setPage(1); load(); }}>Qidirish</button>
        </div>
      )}

      <div className="panel table-wrap">
        {tab === "access" ? (
          <table>
            <thead>
              <tr><th>Vaqt</th><th>Foydalanuvchi</th><th>Metod</th><th>Natija</th><th>Tafsilot</th></tr>
            </thead>
            <tbody>
              {access.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                  <td>{r.user_id ? <Link to={`/users/${r.user_id}`}>{r.user_name || r.user_id.slice(0, 8)}</Link> : "—"}</td>
                  <td>{r.method}</td>
                  <td>{r.success ? "OK" : "FAIL"}</td>
                  <td className="muted">{r.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr><th>Vaqt</th><th>Admin</th><th>Amal</th><th>Entity</th><th>ID</th></tr>
            </thead>
            <tbody>
              {audit.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                  <td>{r.admin_name || r.admin_id?.slice(0, 8) || "—"}</td>
                  <td>{r.action}</td>
                  <td>{r.entity_type}</td>
                  <td className="muted">{r.entity_id?.slice(0, 8) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="row pager">
        <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Oldingi</button>
        <span className="muted">{total} yozuv · sahifa {page}</span>
        <button className="btn secondary" onClick={() => setPage((p) => p + 1)}>Keyingi</button>
      </div>
    </div>
  );
}
