import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

type Req = { id: string; user_id: string; user_name?: string; status: string; note?: string; created_at?: string };

export function FaceRequestsPage() {
  const [rows, setRows] = useState<Req[]>([]);
  const [status, setStatus] = useState("pending");
  const [error, setError] = useState("");

  const load = () =>
    api.faceRequests(status || undefined).then(setRows).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, [status]);

  return (
    <div>
      <h2>FaceID yangilash so‘rovlari</h2>
      <p className="muted">Talaba/xodim kabinetidan kelgan so‘rovlarni tasdiqlash yoki rad etish.</p>
      {error && <p className="error">{error}</p>}
      <div className="tabs">
        {["pending", "approved", "rejected", ""].map((s) => (
          <button key={s || "all"} className={`tab${status === s ? " active" : ""}`} onClick={() => setStatus(s)}>
            {s || "Barchasi"}
          </button>
        ))}
      </div>
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr><th>Foydalanuvchi</th><th>Izoh</th><th>Status</th><th>Sana</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td><Link to={`/users/${r.user_id}`}>{r.user_name || r.user_id.slice(0, 8)}</Link></td>
                <td>{r.note || "—"}</td>
                <td><span className="badge">{r.status}</span></td>
                <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                <td className="row">
                  {r.status === "pending" && (
                    <>
                      <button className="btn" onClick={async () => { await api.reviewFaceRequest(r.id, true); load(); }}>Tasdiqlash</button>
                      <button className="btn danger" onClick={async () => { await api.reviewFaceRequest(r.id, false); load(); }}>Rad etish</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={5} className="muted">So‘rov yo‘q</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
