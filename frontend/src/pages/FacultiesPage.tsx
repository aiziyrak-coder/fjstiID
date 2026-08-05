import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type Fac = { id: string; name: string; code?: string; departments_count?: number };

export function FacultiesPage() {
  const [rows, setRows] = useState<Fac[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = () => api.faculties().then(setRows).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editId) {
        await api.updateFaculty(editId, { name, code: code || null });
      } else {
        await api.createFaculty({ name, code: code || null });
      }
      setName("");
      setCode("");
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  return (
    <div>
      <h2>Fakultetlar</h2>
      <p className="muted">Fakultet qo‘shish / tahrirlash. Keyin unga kafedralar biriktiriladi.</p>
      {error && <p className="error">{error}</p>}

      <form className="panel form-grid" onSubmit={submit} style={{ marginBottom: "1rem" }}>
        <label>
          Fakultet nomi *
          <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Davolash ishi fakulteti" />
        </label>
        <label>
          Kod
          <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="DI" />
        </label>
        <div className="row" style={{ alignItems: "end" }}>
          <button className="btn">{editId ? "Saqlash" : "Qo'shish"}</button>
          {editId && (
            <button
              type="button"
              className="btn secondary"
              onClick={() => {
                setEditId(null);
                setName("");
                setCode("");
              }}
            >
              Bekor
            </button>
          )}
        </div>
      </form>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Nomi</th>
              <th>Kod</th>
              <th>Kafedralar</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id}>
                <td>
                  <strong>{f.name}</strong>
                </td>
                <td>{f.code || "—"}</td>
                <td>{f.departments_count ?? 0}</td>
                <td className="row">
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setEditId(f.id);
                      setName(f.name);
                      setCode(f.code || "");
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="btn danger"
                    onClick={async () => {
                      if (!confirm("O'chirish?")) return;
                      await api.deleteFaculty(f.id);
                      load();
                    }}
                  >
                    O'chirish
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
