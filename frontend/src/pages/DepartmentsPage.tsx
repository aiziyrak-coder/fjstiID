import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type Dept = {
  id: string;
  name: string;
  code?: string;
  faculty_id?: string;
  faculty_name?: string;
  groups_count?: number;
  staff_count?: number;
};

export function DepartmentsPage() {
  const [rows, setRows] = useState<Dept[]>([]);
  const [faculties, setFaculties] = useState<{ id: string; name: string }[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [facultyId, setFacultyId] = useState("");
  const [filterFac, setFilterFac] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    api
      .departments(filterFac || undefined)
      .then(setRows)
      .catch((e) => setError(e.message));

  useEffect(() => {
    api.faculties().then(setFaculties);
  }, []);

  useEffect(() => {
    load();
  }, [filterFac]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const body = { name, code: code || null, faculty_id: facultyId };
      if (editId) await api.updateDepartment(editId, body);
      else await api.createDepartment(body);
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
      <h2>Kafedralar / bo‘limlar</h2>
      <p className="muted">Har bir kafedra fakultetga birikadi. Xodimlar shu kafedraga, guruhlar ham shu kafedraga bog‘lanadi.</p>
      {error && <p className="error">{error}</p>}

      <div className="row" style={{ marginBottom: "1rem" }}>
        <select value={filterFac} onChange={(e) => setFilterFac(e.target.value)}>
          <option value="">Barcha fakultetlar</option>
          {faculties.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>

      <form className="panel form-grid" onSubmit={submit} style={{ marginBottom: "1rem" }}>
        <label>
          Fakultet *
          <select required value={facultyId} onChange={(e) => setFacultyId(e.target.value)}>
            <option value="">Tanlang</option>
            {faculties.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Kafedra nomi *
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Kod
          <input value={code} onChange={(e) => setCode(e.target.value)} />
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
              <th>Kafedra</th>
              <th>Fakultet</th>
              <th>Guruhlar</th>
              <th>Xodimlar</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td>
                  <strong>{d.name}</strong> {d.code ? <code>{d.code}</code> : null}
                </td>
                <td>{d.faculty_name || "—"}</td>
                <td>{d.groups_count ?? 0}</td>
                <td>{d.staff_count ?? 0}</td>
                <td className="row">
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setEditId(d.id);
                      setName(d.name);
                      setCode(d.code || "");
                      setFacultyId(d.faculty_id || "");
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="btn danger"
                    onClick={async () => {
                      if (!confirm("O'chirish?")) return;
                      await api.deleteDepartment(d.id);
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
