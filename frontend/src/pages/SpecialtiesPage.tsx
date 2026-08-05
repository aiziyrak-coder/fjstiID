import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type Row = { id: string; name: string; code?: string; faculty_id?: string; faculty_name?: string };

export function SpecialtiesPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [faculties, setFaculties] = useState<{ id: string; name: string }[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [facultyId, setFacultyId] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = () => api.specialties().then(setRows).catch((e) => setError(e.message));
  useEffect(() => {
    load();
    api.faculties().then(setFaculties);
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const body = { name, code: code || null, faculty_id: facultyId || null };
      if (editId) await api.updateSpecialty(editId, body);
      else await api.createSpecialty(body);
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
      <h2>Yo‘nalishlar / mutaxassisliklar</h2>
      <p className="muted">Fakultetga biriktiriladi. Talaba kartochkasida ixtiyoriy.</p>
      {error && <p className="error">{error}</p>}
      <form className="panel form-grid" onSubmit={submit}>
        <label>Nomi *<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>Kod<input value={code} onChange={(e) => setCode(e.target.value)} /></label>
        <label>
          Fakultet
          <select value={facultyId} onChange={(e) => setFacultyId(e.target.value)}>
            <option value="">—</option>
            {faculties.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
        </label>
        <div className="row" style={{ alignItems: "end" }}>
          <button className="btn">{editId ? "Saqlash" : "Qo'shish"}</button>
        </div>
      </form>
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr><th>Nomi</th><th>Kod</th><th>Fakultet</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.code || "—"}</td>
                <td>{r.faculty_name || "—"}</td>
                <td className="row">
                  <button className="btn secondary" onClick={() => { setEditId(r.id); setName(r.name); setCode(r.code || ""); setFacultyId(r.faculty_id || ""); }}>Edit</button>
                  <button className="btn danger" onClick={async () => { if (confirm("O‘chirish?")) { await api.deleteSpecialty(r.id); load(); } }}>O‘chirish</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
