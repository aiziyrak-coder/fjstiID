import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

export function ClientsPage() {
  const [clients, setClients] = useState<any[]>([]);
  const [created, setCreated] = useState<any | null>(null);
  const [name, setName] = useState("");
  const [webhook, setWebhook] = useState("");
  const [error, setError] = useState("");

  const load = () => api.clients().then(setClients).catch((e) => setError(e.message));

  useEffect(() => {
    void load();
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.createClient({
        name,
        webhook_url: webhook || null,
        redirect_uris: ["http://localhost:5173/oauth/callback", "http://localhost:3001/callback"],
        allowed_fields: ["id", "full_name", "roles", "email", "student", "staff"],
      });
      setCreated(res);
      setName("");
      setWebhook("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  return (
    <div>
      <h2>Ulangan dasturlar (SSO / API)</h2>
      <p className="muted">Davomat, LMS va boshqa tizimlar uchun OAuth2 client.</p>
      {error && <p className="error">{error}</p>}
      <form className="panel form-grid" onSubmit={onCreate} style={{ marginBottom: "1rem" }}>
        <label>Dastur nomi *<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
        <label>Webhook URL<input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://..." /></label>
        <div style={{ alignSelf: "end" }}><button className="btn">Yaratish</button></div>
      </form>
      {created && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "var(--accent)" }}>
          <strong>Kalitlar bir marta ko'rsatiladi — saqlang!</strong>
          <p>client_id: {created.client_id}</p>
          <p>client_secret: {created.client_secret}</p>
          <p>api_key: {created.api_key}</p>
        </div>
      )}
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Nomi</th>
              <th>client_id</th>
              <th>Scopes</th>
              <th>Webhook</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td><code>{c.client_id}</code></td>
                <td>{(c.allowed_scopes || []).join(", ")}</td>
                <td className="muted">{c.webhook_url || "—"}</td>
                <td>{c.is_active ? "faol" : "o'chirilgan"}</td>
                <td>
                  {c.is_active && (
                    <button
                      className="btn danger"
                      onClick={async () => {
                        if (!confirm("Deaktivlashtirish?")) return;
                        await api.deleteClient(c.id);
                        load();
                      }}
                    >
                      O‘chirish
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
