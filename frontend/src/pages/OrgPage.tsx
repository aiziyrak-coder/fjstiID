import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";

export function OrgPage() {
  const [faculties, setFaculties] = useState<{ id: string; name: string; code?: string }[]>([]);
  const [specialties, setSpecialties] = useState<{ id: string; name: string; code?: string }[]>([]);
  const [groups, setGroups] = useState<{ id: string; name: string; course?: number }[]>([]);
  const [departments, setDepartments] = useState<{ id: string; name: string; code?: string }[]>([]);
  const [facName, setFacName] = useState("");
  const [specName, setSpecName] = useState("");
  const [groupName, setGroupName] = useState("");
  const [deptName, setDeptName] = useState("");

  const load = async () => {
    setFaculties(await api.faculties());
    setSpecialties(await api.specialties());
    setGroups(await api.groups());
    setDepartments(await api.departments());
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <h2>Tashkiliy tuzilma</h2>
      <p className="muted">Fakultet → yo'nalish → guruh · Kafedra/bo'lim (xodimlar uchun)</p>
      <div className="stats" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <form
          className="panel"
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            await api.createFaculty({ name: facName });
            setFacName("");
            await load();
          }}
        >
          <h3>Fakultetlar</h3>
          <ul>
            {faculties.map((f) => (
              <li key={f.id}>
                {f.name} {f.code ? `(${f.code})` : ""}
              </li>
            ))}
          </ul>
          <input value={facName} onChange={(e) => setFacName(e.target.value)} placeholder="Yangi fakultet" required />
          <button className="btn" style={{ marginTop: 8 }}>
            Qo'shish
          </button>
        </form>

        <form
          className="panel"
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            await api.createSpecialty({ name: specName, faculty_id: faculties[0]?.id });
            setSpecName("");
            await load();
          }}
        >
          <h3>Yo'nalishlar</h3>
          <ul>
            {specialties.map((s) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
          <input value={specName} onChange={(e) => setSpecName(e.target.value)} placeholder="Yangi yo'nalish" required />
          <button className="btn" style={{ marginTop: 8 }}>
            Qo'shish
          </button>
        </form>

        <form
          className="panel"
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            await api.createGroup({ name: groupName, course: 1, faculty_id: faculties[0]?.id });
            setGroupName("");
            await load();
          }}
        >
          <h3>Guruhlar</h3>
          <ul>
            {groups.map((g) => (
              <li key={g.id}>
                {g.name} {g.course ? `— ${g.course}-kurs` : ""}
              </li>
            ))}
          </ul>
          <input value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="Yangi guruh" required />
          <button className="btn" style={{ marginTop: 8 }}>
            Qo'shish
          </button>
        </form>

        <form
          className="panel"
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            await api.createDepartment({ name: deptName });
            setDeptName("");
            await load();
          }}
        >
          <h3>Kafedralar / bo'limlar</h3>
          <ul>
            {departments.map((d) => (
              <li key={d.id}>
                {d.name} {d.code ? `(${d.code})` : ""}
              </li>
            ))}
          </ul>
          <input value={deptName} onChange={(e) => setDeptName(e.target.value)} placeholder="Yangi kafedra" required />
          <button className="btn" style={{ marginTop: 8 }}>
            Qo'shish
          </button>
        </form>
      </div>
    </div>
  );
}
