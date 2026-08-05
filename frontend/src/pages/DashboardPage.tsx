import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, type DashboardStats } from "../api";
import { useAuth } from "../auth";

export function DashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [s, setS] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api.stats().then(setS).catch(console.error);
  }, []);

  if (!s) return <p className="muted">Yuklanmoqda...</p>;

  const maxBar = Math.max(1, ...s.access_last_7_days.map((d) => d.success + d.fail));
  const maxFac = Math.max(1, ...s.by_faculty.map((f) => f.students + f.staff));

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="muted">{t("welcome")} · {user?.full_name}</div>
          <h2 style={{ margin: "0.25rem 0 0" }}>Dashboard</h2>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            FJSTI ID — to‘liq universitet analitikasi
            {s.current_academic_year ? ` · O‘quv yili: ${s.current_academic_year}` : ""}
          </p>
        </div>
        <div className="row">
          <Link className="btn secondary" to="/face-requests">
            Face so‘rovlar ({s.face_pending_requests})
          </Link>
          <Link className="btn" to="/users">
            Foydalanuvchilar
          </Link>
        </div>
      </div>

      <h3 className="section-title">Foydalanuvchilar</h3>
      <div className="stats">
        {[
          ["Jami shaxslar", s.total_users],
          ["Faqat talaba", s.students_only],
          ["Faqat xodim", s.staff_only],
          ["Talaba + xodim", s.student_and_staff],
          ["Faol", s.active_users],
          ["Nofaol", s.inactive_users],
          ["FaceID bor", s.face_enrolled],
          ["Talaba Face yo‘q", s.no_face_students],
        ].map(([label, value], i) => (
          <div className="stat" key={String(label)} style={{ animationDelay: `${i * 30}ms` }}>
            <strong>{value as number}</strong>
            <span>{label as string}</span>
          </div>
        ))}
      </div>

      <h3 className="section-title">Tashkilot</h3>
      <div className="stats">
        {[
          ["Fakultetlar", s.faculties],
          ["Kafedralar", s.departments],
          ["Guruhlar", s.groups],
          ["Yo‘nalishlar", s.specialties],
          ["Ulangan dasturlar", s.client_apps],
        ].map(([label, value]) => (
          <div className="stat" key={String(label)}>
            <strong>{value as number}</strong>
            <span>{label as string}</span>
          </div>
        ))}
      </div>

      <h3 className="section-title">So‘rovlar / kirishlar</h3>
      <div className="stats">
        {[
          ["Bugun (OK)", s.access_today],
          ["Bugun (xato)", s.access_today_fail],
          ["Jami so‘rovlar", s.access_total],
          ["FaceID", s.access_face],
          ["Parol", s.access_password],
          ["QR", s.access_qr],
          ["Admin amallar", s.audit_total],
          ["Face kutilmoqda", s.face_pending_requests],
        ].map(([label, value]) => (
          <div className="stat" key={String(label)}>
            <strong>{value as number}</strong>
            <span>{label as string}</span>
          </div>
        ))}
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Oxirgi 7 kun</h3>
          <div className="bars">
            {s.access_last_7_days.map((d) => (
              <div key={d.date} className="bar-col">
                <div className="bar-stack">
                  <div className="bar ok" style={{ height: `${(d.success / maxBar) * 100 || 2}%` }} />
                  <div className="bar fail" style={{ height: `${(d.fail / maxBar) * 100 || 0}%` }} />
                </div>
                <span className="bar-label">{d.date.slice(5)}</span>
                <span className="bar-num">{d.success + d.fail}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Fakultetlar bo‘yicha</h3>
          {s.by_faculty.length === 0 && <p className="muted">Ma’lumot yo‘q</p>}
          {s.by_faculty.map((f) => (
            <div key={f.faculty_id} className="fac-row">
              <div className="fac-head">
                <strong>{f.faculty_name}</strong>
                <span className="muted">
                  {f.students} talaba · {f.staff} xodim · {f.groups} guruh
                </span>
              </div>
              <div className="fac-bar">
                <div style={{ width: `${((f.students + f.staff) / maxFac) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {s.by_status.length > 0 && (
        <>
          <h3 className="section-title">Status taqsimoti</h3>
          <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
            {s.by_status.map((x) => (
              <span key={x.status} className="badge">
                {x.status}: {x.count}
              </span>
            ))}
          </div>
        </>
      )}

      <div className="row" style={{ marginTop: "1.5rem" }}>
        <Link className="btn secondary" to="/faculties">
          Fakultetlar
        </Link>
        <Link className="btn secondary" to="/departments">
          Kafedralar
        </Link>
        <Link className="btn secondary" to="/groups">
          Guruhlar
        </Link>
        <Link className="btn secondary" to="/specialties">
          Yo‘nalishlar
        </Link>
        <Link className="btn secondary" to="/logs">
          Jurnallar
        </Link>
        <Link className="btn secondary" to="/settings">
          Sozlamalar
        </Link>
      </div>
    </div>
  );
}
