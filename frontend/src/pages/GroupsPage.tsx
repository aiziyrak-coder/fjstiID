import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

type Grp = {
  id: string;
  name: string;
  department_id?: string;
  department_name?: string;
  faculty_name?: string;
  students_count?: number;
  academic_year?: string;
};

export function GroupsPage() {
  const [rows, setRows] = useState<Grp[]>([]);
  const [departments, setDepartments] = useState<{ id: string; name: string; faculty_name?: string }[]>([]);
  const [name, setName] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [year, setYear] = useState("2025/2026");
  const [filterDept, setFilterDept] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    api
      .groups(filterDept ? { department_id: filterDept } : undefined)
      .then(setRows)
      .catch((e) => setError(e.message));

  useEffect(() => {
    api.departments().then(setDepartments);
  }, []);

  useEffect(() => {
    load();
  }, [filterDept]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const body = { name, department_id: departmentId, academic_year: year || null };
      if (editId) await api.updateGroup(editId, body);
      else await api.createGroup(body);
      setName("");
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  return (
    <div>
      <h2>Guruhlar</h2>
      <p className="muted">
        Guruh kafedraga birikadi. Talaba qo‘shishda guruh tanlanadi (kurs saqlanmaydi — har yili o‘zgaradi).
      </p>
      {error && <p className="error">{error}</p>}

      <div className="row" style={{ marginBottom: "1rem" }}>
        <select value={filterDept} onChange={(e) => setFilterDept(e.target.value)}>
          <option value="">Barcha kafedralar</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} {d.faculty_name ? `(${d.faculty_name})` : ""}
            </option>
          ))}
        </select>
      </div>

      <form className="panel form-grid" onSubmit={submit} style={{ marginBottom: "1rem" }}>
        <label>
          Kafedra *
          <select required value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
            <option value="">Tanlang</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Guruh nomi *
          <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="DI-101" />
        </label>
        <label>
          O'quv yili
          <input value={year} onChange={(e) => setYear(e.target.value)} placeholder="2025/2026" />
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
              <th>Guruh</th>
              <th>Kafedra</th>
              <th>Fakultet</th>
              <th>O'quv yili</th>
              <th>Talabalar</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((g) => (
              <tr key={g.id}>
                <td>
                  <strong>{g.name}</strong>
                </td>
                <td>{g.department_name || "—"}</td>
                <td>{g.faculty_name || "—"}</td>
                <td>{g.academic_year || "—"}</td>
                <td>{g.students_count ?? 0}</td>
                <td className="row">
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setEditId(g.id);
                      setName(g.name);
                      setDepartmentId(g.department_id || "");
                      setYear(g.academic_year || "");
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="btn danger"
                    onClick={async () => {
                      if (!confirm("O'chirish?")) return;
                      await api.deleteGroup(g.id);
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
