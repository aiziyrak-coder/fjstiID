import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

export function UserDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [u, setU] = useState<any>(null);
  const [edit, setEdit] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [faculties, setFaculties] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [password, setPassword] = useState("");

  const [form, setForm] = useState({
    last_name: "",
    first_name: "",
    middle_name: "",
    gender: "",
    pinfl: "",
    phone: "",
    email: "",
    status: "active",
    notes: "",
    student_number: "",
    faculty_id: "",
    group_id: "",
    study_form: "",
    funding: "",
    academic_status: "active",
    employee_number: "",
    department_id: "",
    position: "",
    staff_status: "active",
    role_student: false,
    role_staff: false,
    role_admin: false,
    role_moderator: false,
  });

  const load = () => {
    if (!id) return;
    api.getUser(id).then((user) => {
      setU(user);
      const roles = (user.roles || []).map((r: any) => r.code);
      setForm({
        last_name: user.last_name || "",
        first_name: user.first_name || "",
        middle_name: user.middle_name || "",
        gender: user.gender || "",
        pinfl: user.pinfl || "",
        phone: user.phone || "",
        email: user.email || "",
        status: user.status || "active",
        notes: user.notes || "",
        student_number: user.student?.student_number || "",
        faculty_id: user.student?.faculty_id || "",
        group_id: user.student?.group_id || "",
        study_form: user.student?.study_form || "",
        funding: user.student?.funding || "",
        academic_status: user.student?.academic_status || "active",
        employee_number: user.staff?.employee_number || "",
        department_id: user.staff?.department_id || "",
        position: user.staff?.position || "",
        staff_status: user.staff?.staff_status || "active",
        role_student: roles.includes("student"),
        role_staff: roles.includes("staff"),
        role_admin: roles.includes("admin"),
        role_moderator: roles.includes("moderator"),
      });
    });
  };

  useEffect(() => {
    load();
    api.faculties().then(setFaculties);
    api.departments().then(setDepartments);
    api.groups().then(setGroups);
  }, [id]);

  if (!u) return <p className="muted">Yuklanmoqda...</p>;

  const apiBase = import.meta.env.VITE_API_URL || "";
  const photoSrc = u.photo_url ? `${apiBase}${u.photo_url}` : null;

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const role_codes: string[] = [];
      if (form.role_student) role_codes.push("student");
      if (form.role_staff) role_codes.push("staff");
      if (form.role_admin) role_codes.push("admin");
      if (form.role_moderator) role_codes.push("moderator");
      const body: any = {
        person: {
          last_name: form.last_name,
          first_name: form.first_name,
          middle_name: form.middle_name || null,
          gender: form.gender || null,
          pinfl: form.pinfl || null,
          notes: form.notes || null,
        },
        contacts: { phone: form.phone || null, email: form.email || null },
        status: form.status,
        role_codes,
      };
      if (form.role_student && form.student_number) {
        body.student = {
          student_number: form.student_number,
          faculty_id: form.faculty_id || null,
          group_id: form.group_id || null,
          study_form: form.study_form || null,
          funding: form.funding || null,
          academic_status: form.academic_status,
        };
      }
      if (form.role_staff && form.employee_number) {
        body.staff = {
          employee_number: form.employee_number,
          department_id: form.department_id || null,
          position: form.position || null,
          staff_status: form.staff_status,
        };
      }
      await api.updateUser(u.id, body);
      setMsg("Saqlandi");
      setEdit(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xato");
    }
  };

  const onPhoto = async (file: File | null) => {
    if (!file || !id) return;
    try {
      await api.uploadPhoto(id, file);
      setMsg("Rasm saqlandi va FaceID ro'yxatga olindi");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rasm xato");
    }
  };

  const onFace = async (file: File | null) => {
    if (!file || !id) return;
    try {
      await api.enrollFace(id, file);
      setMsg("FaceID yangilandi");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Face xato");
    }
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <Link to="/users" className="muted">← Foydalanuvchilar</Link>
          <h2 style={{ margin: "0.35rem 0 0" }}>{u.full_name}</h2>
          <div className="row" style={{ gap: 6, marginTop: 6 }}>
            {(u.roles || []).map((r: any) => (
              <span key={r.code} className="badge">{r.name_uz || r.code}</span>
            ))}
            <span className={`badge status-${u.status}`}>{u.status}</span>
            {u.has_face && <span className="badge">FaceID</span>}
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn secondary" onClick={() => setEdit((v) => !v)}>{edit ? "Bekor" : "Tahrirlash"}</button>
          <button className="btn secondary" onClick={() => api.openIdCard(u.id)}>ID karta</button>
          <button
            className="btn danger"
            onClick={async () => {
              if (!confirm("Arxivlash?")) return;
              await api.deleteUser(u.id);
              nav("/users");
            }}
          >
            Arxivlash
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {msg && <p className="ok-msg">{msg}</p>}

      <div className="detail-grid">
        <div className="panel">
          <div className="photo-box">
            {photoSrc ? <img src={photoSrc} alt="" /> : <div className="photo-placeholder">Rasm yo‘q</div>}
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <label className="btn secondary" style={{ cursor: "pointer" }}>
              Rasm + FaceID
              <input type="file" accept="image/*" hidden onChange={(e) => onPhoto(e.target.files?.[0] || null)} />
            </label>
            <label className="btn secondary" style={{ cursor: "pointer" }}>
              Faqat Face yangilash
              <input type="file" accept="image/*" hidden onChange={(e) => onFace(e.target.files?.[0] || null)} />
            </label>
          </div>
          {u.has_face ? (
            <p className="ok-msg" style={{ marginTop: 8 }}>FaceID tayyor — tekshiruv mumkin</p>
          ) : (
            <p className="muted" style={{ marginTop: 8 }}>FaceID yo‘q — rasm yuklang</p>
          )}
          <div className="row" style={{ marginTop: 12 }}>
            <input placeholder="Yangi parol" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button
              className="btn secondary"
              onClick={async () => {
                if (password.length < 8) return setError("Parol kamida 8 belgi");
                await api.resetPassword(u.id, password);
                setMsg("Parol yangilandi");
                setPassword("");
              }}
            >
              Parol reset
            </button>
          </div>
        </div>

        {!edit ? (
          <div className="panel">
            <h3 style={{ marginTop: 0 }}>Ma’lumotlar</h3>
            <div className="kv-grid">
              <div className="kv"><span className="muted">JSHSHIR</span><strong>{u.pinfl || "—"}</strong></div>
              <div className="kv"><span className="muted">Telefon</span><strong>{u.phone || "—"}</strong></div>
              <div className="kv"><span className="muted">Email</span><strong>{u.email || "—"}</strong></div>
              <div className="kv"><span className="muted">Pasport</span><strong>{u.document ? `${u.document.series || ""} ${u.document.number || ""}` : "—"}</strong></div>
              {u.student && (
                <>
                  <div className="kv"><span className="muted">Talaba ID</span><strong>{u.student.student_number}</strong></div>
                  <div className="kv"><span className="muted">Fakultet</span><strong>{u.student.faculty_name || "—"}</strong></div>
                  <div className="kv"><span className="muted">Kafedra</span><strong>{u.student.department_name || "—"}</strong></div>
                  <div className="kv"><span className="muted">Guruh</span><strong>{u.student.group_name || "—"}</strong></div>
                </>
              )}
              {u.staff && (
                <>
                  <div className="kv"><span className="muted">Xodim ID</span><strong>{u.staff.employee_number}</strong></div>
                  <div className="kv"><span className="muted">Bo‘lim</span><strong>{u.staff.department_name || "—"}</strong></div>
                  <div className="kv"><span className="muted">Lavozim</span><strong>{u.staff.position || "—"}</strong></div>
                </>
              )}
            </div>
          </div>
        ) : (
          <form className="panel person-form" onSubmit={save}>
            <h3 style={{ marginTop: 0 }}>Tahrirlash</h3>
            <div className="form-grid">
              <label className="field"><span className="field-label">Familiya</span><input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label>
              <label className="field"><span className="field-label">Ism</span><input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label>
              <label className="field"><span className="field-label">Otasining ismi</span><input value={form.middle_name} onChange={(e) => setForm({ ...form, middle_name: e.target.value })} /></label>
              <label className="field"><span className="field-label">JSHSHIR</span><input value={form.pinfl} onChange={(e) => setForm({ ...form, pinfl: e.target.value })} /></label>
              <label className="field"><span className="field-label">Telefon</span><input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
              <label className="field"><span className="field-label">Email</span><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
              <label className="field">
                <span className="field-label">Status</span>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  {["active", "inactive", "suspended", "graduated", "dismissed", "archived"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="row" style={{ margin: "0.75rem 0" }}>
              {(["student", "staff", "admin", "moderator"] as const).map((r) => (
                <label key={r} className="chip">
                  <input
                    type="checkbox"
                    checked={(form as any)[`role_${r}`]}
                    onChange={(e) => setForm({ ...form, [`role_${r}`]: e.target.checked })}
                  />{" "}
                  {r}
                </label>
              ))}
            </div>
            {form.role_student && (
              <div className="form-grid">
                <label className="field"><span className="field-label">Talaba ID</span><input value={form.student_number} onChange={(e) => setForm({ ...form, student_number: e.target.value })} /></label>
                <label className="field">
                  <span className="field-label">Fakultet</span>
                  <select value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })}>
                    <option value="">—</option>
                    {faculties.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">Guruh</span>
                  <select value={form.group_id} onChange={(e) => setForm({ ...form, group_id: e.target.value })}>
                    <option value="">—</option>
                    {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">Akademik status</span>
                  <select value={form.academic_status} onChange={(e) => setForm({ ...form, academic_status: e.target.value })}>
                    {["active", "academic_leave", "graduated", "expelled"].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </label>
              </div>
            )}
            {form.role_staff && (
              <div className="form-grid">
                <label className="field"><span className="field-label">Xodim ID</span><input value={form.employee_number} onChange={(e) => setForm({ ...form, employee_number: e.target.value })} /></label>
                <label className="field">
                  <span className="field-label">Kafedra</span>
                  <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
                    <option value="">—</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </label>
                <label className="field"><span className="field-label">Lavozim</span><input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} /></label>
              </div>
            )}
            <button className="btn" type="submit">Saqlash</button>
          </form>
        )}
      </div>
    </div>
  );
}
