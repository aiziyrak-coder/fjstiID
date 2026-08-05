import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type Year = { id: string; name: string; is_current: boolean; starts_on?: string; ends_on?: string };

export function AcademicYearsPage() {
  const [rows, setRows] = useState<Year[]>([]);
  const [name, setName] = useState("2025/2026");
  const [isCurrent, setIsCurrent] = useState(true);
  const [error, setError] = useState("");

  const load = () => api.academicYears().then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.createAcademicYear({ name, is_current: isCurrent });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  return (
    <div>
      <h2>O‘quv yillari</h2>
      <p className="muted">Joriy yil guruhlar va hisobotlar uchun asos.</p>
      {error && <p className="error">{error}</p>}
      <form className="panel form-grid" onSubmit={submit}>
        <label>Yil *<input required value={name} onChange={(e) => setName(e.target.value)} placeholder="2025/2026" /></label>
        <label className="chip" style={{ alignSelf: "end" }}>
          <input type="checkbox" checked={isCurrent} onChange={(e) => setIsCurrent(e.target.checked)} /> Joriy yil
        </label>
        <div style={{ alignSelf: "end" }}><button className="btn">Qo'shish</button></div>
      </form>
      <div className="panel table-wrap">
        <table>
          <thead><tr><th>Yil</th><th>Joriy</th><th></th></tr></thead>
          <tbody>
            {rows.map((y) => (
              <tr key={y.id}>
                <td>{y.name}</td>
                <td>{y.is_current ? "✓" : "—"}</td>
                <td className="row">
                  {!y.is_current && (
                    <button className="btn secondary" onClick={async () => { await api.updateAcademicYear(y.id, { name: y.name, is_current: true }); load(); }}>
                      Joriy qilish
                    </button>
                  )}
                  <button className="btn danger" onClick={async () => { if (confirm("O‘chirish?")) { await api.deleteAcademicYear(y.id); load(); } }}>O‘chirish</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
