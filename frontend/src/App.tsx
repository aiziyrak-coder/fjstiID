import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "./auth";

export function AppLayout() {
  const { t, i18n } = useTranslation();
  const { user, logout, loading, isAdmin } = useAuth();

  if (loading) return <div className="login-page">Yuklanmoqda...</div>;
  if (!user) return <Navigate to="/login" replace />;

  const adminGroups = [
    {
      title: "Asosiy",
      links: [
        ["/", "Dashboard"],
        ["/users", "Foydalanuvchilar"],
        ["/face-requests", "Face so'rovlar"],
      ],
    },
    {
      title: "Tashkilot",
      links: [
        ["/faculties", "Fakultetlar"],
        ["/departments", "Kafedralar"],
        ["/groups", "Guruhlar"],
        ["/specialties", "Yo'nalishlar"],
        ["/years", "O'quv yillari"],
      ],
    },
    {
      title: "Tizim",
      links: [
        ["/clients", "Dasturlar"],
        ["/face", "FaceID kiosk"],
        ["/logs", "Jurnallar"],
        ["/settings", "Sozlamalar"],
        ["/portal", "Mening kabinetim"],
      ],
    },
  ] as const;

  const userLinks = [
    ["/", "Bosh sahifa"],
    ["/face", "FaceID"],
    ["/portal", "Mening kabinetim"],
  ] as const;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">FJSTI ID</div>
        <div className="brand-sub">Universitet admin</div>
        <nav className="side-nav">
          {isAdmin
            ? adminGroups.map((g) => (
                <div key={g.title} className="nav-group">
                  <div className="nav-group-title">{g.title}</div>
                  {g.links.map(([to, label]) => (
                    <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                      {label}
                    </NavLink>
                  ))}
                </div>
              ))
            : userLinks.map(([to, label]) => (
                <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                  {label}
                </NavLink>
              ))}
        </nav>
        <div className="sidebar-foot">
          <select
            value={i18n.language}
            onChange={(e) => {
              i18n.changeLanguage(e.target.value);
              localStorage.setItem("lang", e.target.value);
            }}
            style={{ width: "100%", marginBottom: 8 }}
          >
            <option value="uz">O'zbek</option>
            <option value="ru">Русский</option>
            <option value="en">English</option>
          </select>
          <button
            className="btn secondary"
            style={{ width: "100%", color: "#fff", borderColor: "rgba(255,255,255,.3)" }}
            onClick={logout}
          >
            {t("logout")}
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
