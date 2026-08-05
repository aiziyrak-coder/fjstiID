import { FormEvent, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, type UserListItem } from "../api";

type Kind = "all" | "students" | "staff" | "both";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

export function UsersPage() {
  const nav = useNavigate();
  const [kind, setKind] = useState<Kind>("all");
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [facultyId, setFacultyId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [hasFace, setHasFace] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [faculties, setFaculties] = useState<{ id: string; name: string }[]>([]);
  const [departments, setDepartments] = useState<{ id: string; name: string; faculty_id?: string }[]>([]);
  const [groups, setGroups] = useState<{ id: string; name: string; department_id?: string }[]>([]);

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string>("");

  const [form, setForm] = useState({
    last_name: "",
    first_name: "",
    middle_name: "",
    gender: "",
    pinfl: "",
    phone: "",
    email: "",
    password: "ChangeMe123!",
    role_student: true,
    role_staff: false,
    student_number: "",
    faculty_id: "",
    department_id: "",
    group_id: "",
    study_form: "kunduzgi",
    funding: "kontrakt",
    employee_number: "",
    staff_department_id: "",
    position: "",
    doc_series: "",
    doc_number: "",
    region: "Farg'ona",
    district: "",
    address_full: "",
  });

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const load = () =>
    api
      .users({
        q: q || undefined,
        kind: kind === "all" ? undefined : kind,
        status: status || undefined,
        faculty_id: facultyId || undefined,
        department_id: departmentId || undefined,
        group_id: groupId || undefined,
        has_face: hasFace === "" ? undefined : hasFace === "1",
        page,
        page_size: 25,
      })
      .then((r) => {
        setUsers(r.items);
        setTotal(r.total);
        setPages(r.pages);
        setSelected(new Set());
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, [kind, page, status, facultyId, departmentId, groupId, hasFace]);

  useEffect(() => {
    api.faculties().then(setFaculties);
    api.departments().then(setDepartments);
    api.groups().then(setGroups);
  }, []);

  const deptsForFaculty = departments.filter((d) => !form.faculty_id || d.faculty_id === form.faculty_id);
  const groupsForDept = groups.filter((g) => !form.department_id || g.department_id === form.department_id);
  const filterDepts = departments.filter((d) => !facultyId || d.faculty_id === facultyId);
  const filterGroups = groups.filter((g) => !departmentId || g.department_id === departmentId);

  const toggle = (id: string) =>
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const bulk = async (action: string, extra?: Record<string, string>) => {
    if (!selected.size) return;
    setError("");
    try {
      const r = await api.bulkUsers({ user_ids: [...selected], action, ...extra });
      setMsg(r.message);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xato");
    }
  };

  const onImport = async (file: File | null) => {
    if (!file) return;
    setError("");
    try {
      const r = await api.importUsers(file);
      setMsg(`Import: ${r.created} yaratildi, ${r.skipped} o‘tkazib yuborildi`);
      if (r.errors.length) setError(r.errors.slice(0, 5).join("; "));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import xato");
    }
  };

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (!photoFile) throw new Error("Rasm majburiy — FaceID shu rasm bilan ishlaydi");
      const role_codes: string[] = [];
      if (form.role_student) role_codes.push("student");
      if (form.role_staff) role_codes.push("staff");
      if (!role_codes.length) throw new Error("Kamida bitta rol");

      const body: Record<string, unknown> = {
        person: {
          last_name: form.last_name,
          first_name: form.first_name,
          middle_name: form.middle_name || null,
          gender: form.gender || null,
          pinfl: form.pinfl || null,
          citizenship: "O'zbekiston",
        },
        contacts: { phone: form.phone || null, email: form.email || null },
        document: { doc_type: "passport", series: form.doc_series || null, number: form.doc_number || null },
        address: { region: form.region || null, district: form.district || null, full_text: form.address_full || null },
        role_codes,
        password: form.password,
        grant_biometric_consent: true,
      };
      if (form.role_student) {
        if (!form.student_number) throw new Error("Talaba ID majburiy");
        if (!form.group_id) throw new Error("Guruh tanlash majburiy");
        body.student = {
          student_number: form.student_number,
          faculty_id: form.faculty_id || null,
          group_id: form.group_id,
          study_form: form.study_form,
          funding: form.funding,
          education_level: "bakalavr",
        };
      }
      if (form.role_staff) {
        if (!form.employee_number) throw new Error("Xodim ID majburiy");
        if (!form.staff_department_id) throw new Error("Kafedra/bo'lim majburiy");
        body.staff = {
          employee_number: form.employee_number,
          department_id: form.staff_department_id,
          position: form.position || null,
          employment_type: "asosiy",
        };
      }
      const created = await api.createUser(body);
      // Rasm + FaceID enroll (birga)
      await api.uploadPhoto(created.id, photoFile);
      setShowForm(false);
      setPhotoFile(null);
      setPhotoPreview("");
      await load();
      nav(`/users/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  const tabs: { id: Kind; label: string }[] = [
    { id: "all", label: "Barchasi" },
    { id: "students", label: "Talabalar" },
    { id: "staff", label: "Xodimlar" },
    { id: "both", label: "Talaba + Xodim" },
  ];

  return (
    <div>
      <div className="topbar">
        <div>
          <h2 style={{ margin: 0 }}>Foydalanuvchilar</h2>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            {total} ta · kuchli filtr, import/export, bulk
          </p>
        </div>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn secondary" onClick={() => api.downloadImportTemplate()}>
            CSV shablon
          </button>
          <label className="btn secondary" style={{ cursor: "pointer" }}>
            Import CSV
            <input
              type="file"
              accept=".csv"
              hidden
              onChange={(e) => onImport(e.target.files?.[0] || null)}
            />
          </label>
          <button className="btn secondary" onClick={() => api.downloadExport({ kind: kind === "all" ? undefined : kind, faculty_id: facultyId || undefined })}>
            Export CSV
          </button>
          <button className="btn" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Yopish" : "+ Qo'shish"}
          </button>
        </div>
      </div>

      <div className="tabs">
        {tabs.map((t) => (
          <button key={t.id} type="button" className={`tab${kind === t.id ? " active" : ""}`} onClick={() => { setKind(t.id); setPage(1); }}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="panel filters">
        <input placeholder="Qidirish: F.I.Sh, ID, JSHSHIR..." value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Status — hammasi</option>
          {["active", "inactive", "suspended", "graduated", "dismissed"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={facultyId} onChange={(e) => { setFacultyId(e.target.value); setDepartmentId(""); setGroupId(""); setPage(1); }}>
          <option value="">Fakultet</option>
          {faculties.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
        <select value={departmentId} onChange={(e) => { setDepartmentId(e.target.value); setGroupId(""); setPage(1); }}>
          <option value="">Kafedra</option>
          {filterDepts.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <select value={groupId} onChange={(e) => { setGroupId(e.target.value); setPage(1); }}>
          <option value="">Guruh</option>
          {filterGroups.map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
        <select value={hasFace} onChange={(e) => { setHasFace(e.target.value); setPage(1); }}>
          <option value="">FaceID</option>
          <option value="1">Bor</option>
          <option value="0">Yo‘q</option>
        </select>
        <button className="btn secondary" onClick={() => { setPage(1); load(); }}>
          Qidirish
        </button>
      </div>

      {selected.size > 0 && (
        <div className="bulk-bar row">
          <span>{selected.size} tanlandi</span>
          <button className="btn secondary" onClick={() => bulk("activate")}>Faollashtirish</button>
          <button className="btn secondary" onClick={() => bulk("deactivate")}>Nofaollashtirish</button>
          <button className="btn danger" onClick={() => bulk("archive")}>Arxivlash</button>
          <button className="btn secondary" onClick={() => bulk("set_status", { status: "suspended" })}>Suspend</button>
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {msg && <p className="ok-msg">{msg}</p>}

      {showForm && (
        <form className="panel person-form" onSubmit={onCreate}>
          <h3 style={{ marginTop: 0 }}>Yangi foydalanuvchi</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            Rasm majburiy — FaceID shu rasm bilan solishtiriladi.
          </p>
          <div className="role-chips row" style={{ marginBottom: "1rem" }}>
            <label className="chip">
              <input type="checkbox" checked={form.role_student} onChange={(e) => set("role_student", e.target.checked)} /> Talaba
            </label>
            <label className="chip">
              <input type="checkbox" checked={form.role_staff} onChange={(e) => set("role_staff", e.target.checked)} /> Xodim
            </label>
          </div>

          <h4>Rasm / FaceID *</h4>
          <div className="row" style={{ marginBottom: "1rem", alignItems: "flex-start" }}>
            <div className="photo-box" style={{ maxWidth: 120 }}>
              {photoPreview ? (
                <img src={photoPreview} alt="preview" />
              ) : (
                <div className="photo-placeholder">Rasm</div>
              )}
            </div>
            <label className="field" style={{ flex: 1 }}>
              <span className="field-label">Yuz aniq ko‘rinadigan rasm (jpg/png)</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
                onChange={(e) => {
                  const f = e.target.files?.[0] || null;
                  setPhotoFile(f);
                  if (photoPreview) URL.revokeObjectURL(photoPreview);
                  setPhotoPreview(f ? URL.createObjectURL(f) : "");
                }}
              />
            </label>
          </div>

          <h4>Shaxs</h4>
          <div className="form-grid">
            <Field label="Familiya *"><input required value={form.last_name} onChange={(e) => set("last_name", e.target.value)} /></Field>
            <Field label="Ism *"><input required value={form.first_name} onChange={(e) => set("first_name", e.target.value)} /></Field>
            <Field label="Otasining ismi"><input value={form.middle_name} onChange={(e) => set("middle_name", e.target.value)} /></Field>
            <Field label="Jinsi">
              <select value={form.gender} onChange={(e) => set("gender", e.target.value)}>
                <option value="">—</option>
                <option value="male">Erkak</option>
                <option value="female">Ayol</option>
              </select>
            </Field>
            <Field label="JSHSHIR"><input value={form.pinfl} onChange={(e) => set("pinfl", e.target.value)} maxLength={14} /></Field>
            <Field label="Telefon"><input value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
            <Field label="Email"><input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} /></Field>
            <Field label="Parol"><input value={form.password} onChange={(e) => set("password", e.target.value)} /></Field>
          </div>
          {form.role_student && (
            <>
              <h4>Talaba — Fakultet → Kafedra → Guruh</h4>
              <div className="form-grid">
                <Field label="Talaba ID *"><input required value={form.student_number} onChange={(e) => set("student_number", e.target.value)} /></Field>
                <Field label="Fakultet *">
                  <select required value={form.faculty_id} onChange={(e) => { set("faculty_id", e.target.value); set("department_id", ""); set("group_id", ""); }}>
                    <option value="">—</option>
                    {faculties.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                </Field>
                <Field label="Kafedra *">
                  <select required value={form.department_id} onChange={(e) => { set("department_id", e.target.value); set("group_id", ""); }}>
                    <option value="">—</option>
                    {deptsForFaculty.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </Field>
                <Field label="Guruh *">
                  <select required value={form.group_id} onChange={(e) => set("group_id", e.target.value)}>
                    <option value="">—</option>
                    {groupsForDept.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                </Field>
              </div>
            </>
          )}
          {form.role_staff && (
            <>
              <h4>Xodim — kafedra / bo‘lim</h4>
              <div className="form-grid">
                <Field label="Xodim ID *"><input required value={form.employee_number} onChange={(e) => set("employee_number", e.target.value)} /></Field>
                <Field label="Kafedra/bo‘lim *">
                  <select required value={form.staff_department_id} onChange={(e) => set("staff_department_id", e.target.value)}>
                    <option value="">—</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </Field>
                <Field label="Lavozim"><input value={form.position} onChange={(e) => set("position", e.target.value)} /></Field>
              </div>
            </>
          )}
          <button className="btn" type="submit">Saqlash</button>
        </form>
      )}

      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>F.I.Sh</th>
              <th>Rollar</th>
              <th>ID</th>
              <th>Tashkilot</th>
              <th>Status</th>
              <th>Face</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="click-row" onClick={() => nav(`/users/${u.id}`)}>
                <td onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggle(u.id)} />
                </td>
                <td>
                  <strong>{u.full_name}</strong>
                  <div className="muted" style={{ fontSize: "0.8rem" }}>{u.email || u.phone || "—"}</div>
                </td>
                <td>{u.roles.map((r) => <span key={r} className="badge">{r}</span>)}</td>
                <td>{u.student_number || u.employee_number || "—"}</td>
                <td className="muted" style={{ fontSize: "0.85rem" }}>
                  {[u.faculty_name, u.department_name, u.group_name].filter(Boolean).join(" · ") || "—"}
                </td>
                <td><span className={`badge status-${u.status || "active"}`}>{u.status || "active"}</span></td>
                <td>{u.has_face ? "✓" : "—"}</td>
              </tr>
            ))}
            {!users.length && (
              <tr><td colSpan={7} className="muted">Natija yo‘q</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="row pager">
        <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Oldingi</button>
        <span className="muted">Sahifa {page} / {pages}</span>
        <button className="btn secondary" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Keyingi</button>
      </div>
    </div>
  );
}
