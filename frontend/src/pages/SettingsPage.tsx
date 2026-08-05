import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

export function SettingsPage() {
  const [items, setItems] = useState<{ key: string; value: string; label?: string }[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings().then(setItems).catch((e) => setError(e.message));
  }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.saveSettings(items);
      setMsg(r.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  return (
    <div>
      <h2>Sozlamalar</h2>
      <p className="muted">Institut, FaceID chegarasi, default parol va boshqa tizim parametrlari.</p>
      {error && <p className="error">{error}</p>}
      {msg && <p className="ok-msg">{msg}</p>}
      <form className="panel" onSubmit={save}>
        {items.map((it, idx) => (
          <label key={it.key} className="field" style={{ marginBottom: "0.85rem", display: "block" }}>
            <span className="field-label">{it.label || it.key}</span>
            <input
              value={it.value}
              onChange={(e) => {
                const next = [...items];
                next[idx] = { ...it, value: e.target.value };
                setItems(next);
              }}
            />
            <span className="muted" style={{ fontSize: "0.75rem" }}>{it.key}</span>
          </label>
        ))}
        <button className="btn" type="submit">Saqlash</button>
      </form>
    </div>
  );
}
