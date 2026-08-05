import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export function PortalPage() {
  const { user, refresh } = useAuth();
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [emName, setEmName] = useState("");
  const [emPhone, setEmPhone] = useState("");
  const [logs, setLogs] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const apiBase = import.meta.env.VITE_API_URL || "";

  useEffect(() => {
    setPhone(user?.phone || "");
    setEmail(user?.email || "");
    setAddress(user?.address?.full_text || "");
    setEmName(user?.emergency?.full_name || "");
    setEmPhone(user?.emergency?.phone || "");
    api.myAccessLogs().then(setLogs).catch(console.error);
  }, [user]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api.patchMe({
      phone: phone || undefined,
      email: email || undefined,
      address_full: address || undefined,
      emergency: { full_name: emName || undefined, phone: emPhone || undefined },
    });
    await refresh();
    setMsg("Saqlandi");
  };

  if (!user) return null;

  return (
    <div>
      <h2>Mening kabinetim</h2>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ alignItems: "flex-start", gap: "1.5rem" }}>
          {user.photo_url ? (
            <img src={`${apiBase}${user.photo_url}`} alt="" style={{ width: 120, height: 150, objectFit: "cover", borderRadius: 10 }} />
          ) : (
            <div className="photo-placeholder" style={{ width: 120, height: 150 }}>
              Rasm yo'q
            </div>
          )}
          <div style={{ flex: 1 }}>
            <h3 style={{ marginTop: 0 }}>{user.full_name}</h3>
            <p className="muted">
              {user.roles.map((r: { name_uz?: string; code?: string }) => r.name_uz || r.code).join(", ")}
              {user.student && <> · Talaba ID: <code>{user.student.student_number}</code></>}
              {user.staff && <> · Xodim ID: <code>{user.staff.employee_number}</code></>}
            </p>
            <div className="kv-grid">
              <div className="kv">
                <span className="muted">JSHSHIR</span>
                <strong>{user.pinfl || "—"}</strong>
              </div>
              <div className="kv">
                <span className="muted">Pasport</span>
                <strong>
                  {user.document ? `${user.document.series || ""} ${user.document.number || ""}` : "—"}
                </strong>
              </div>
              <div className="kv">
                <span className="muted">Fakultet / kafedra</span>
                <strong>{user.student?.faculty_name || user.staff?.department_name || "—"}</strong>
              </div>
              <div className="kv">
                <span className="muted">QR</span>
                <strong>
                  <code>{user.qr_token}</code>
                </strong>
              </div>
            </div>
          </div>
        </div>

        <form className="form-grid" onSubmit={save} style={{ marginTop: "1.25rem" }}>
          <label>
            Telefon
            <input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </label>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Manzil
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
          </label>
          <label>
            Favqulodda aloqa
            <input value={emName} onChange={(e) => setEmName(e.target.value)} />
          </label>
          <label>
            Favqulodda telefon
            <input value={emPhone} onChange={(e) => setEmPhone(e.target.value)} />
          </label>
          <div className="row" style={{ alignItems: "end" }}>
            <button className="btn">Saqlash</button>
            <button
              type="button"
              className="btn secondary"
              onClick={async () => {
                await api.requestFaceUpdate("Yuz rasmini yangilash");
                setMsg("So'rov yuborildi");
              }}
            >
              Face yangilash so'rovi
            </button>
          </div>
        </form>
        {msg && <p className="muted">{msg}</p>}
      </div>

      <div className="panel">
        <h3>Kirish tarixi</h3>
        <table>
          <thead>
            <tr>
              <th>Vaqt</th>
              <th>Usul</th>
              <th>Natija</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td>{l.created_at}</td>
                <td>{l.method}</td>
                <td>{l.success ? "OK" : "FAIL"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
