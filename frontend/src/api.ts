const API_URL = import.meta.env.VITE_API_URL || "";

export type Role = { id: string; code: string; name?: string; name_uz?: string };
export type UserListItem = {
  id: string;
  full_name: string;
  photo_url?: string | null;
  pinfl?: string | null;
  phone?: string | null;
  email?: string | null;
  roles: string[];
  student_number?: string | null;
  employee_number?: string | null;
  passport?: string | null;
  is_active: boolean;
  status?: string;
  has_face?: boolean;
  faculty_name?: string | null;
  department_name?: string | null;
  group_name?: string | null;
};

export type PageUsers = {
  items: UserListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type User = any;

export type DashboardStats = {
  total_users: number;
  students_only: number;
  staff_only: number;
  student_and_staff: number;
  students_total: number;
  staff_total: number;
  active_users: number;
  inactive_users: number;
  face_enrolled: number;
  face_pending_requests: number;
  no_face_students: number;
  faculties: number;
  departments: number;
  groups: number;
  specialties: number;
  client_apps: number;
  access_today: number;
  access_today_fail: number;
  access_total: number;
  access_face: number;
  access_password: number;
  access_qr: number;
  access_last_7_days: { date: string; success: number; fail: number }[];
  access_last_30_days: { date: string; success: number; fail: number }[];
  audit_total: number;
  by_faculty: { faculty_id: string; faculty_name: string; students: number; staff: number; groups: number; departments: number }[];
  by_status: { status: string; count: number }[];
  current_academic_year?: string | null;
};

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail || err));
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("text/csv") || ct.includes("text/html")) {
    return (await res.text()) as T;
  }
  return res.json();
}

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/v1/auth/me"),
  stats: () => request<DashboardStats>("/api/v1/admin/stats"),
  users: (opts?: Record<string, string | number | boolean | undefined>) =>
    request<PageUsers>(`/api/v1/admin/users${qs(opts || {})}`),
  getUser: (id: string) => request<User>(`/api/v1/admin/users/${id}`),
  createUser: (body: unknown) =>
    request<User>("/api/v1/admin/users", { method: "POST", body: JSON.stringify(body) }),
  updateUser: (id: string, body: unknown) =>
    request<User>(`/api/v1/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteUser: (id: string) => request<{ message: string }>(`/api/v1/admin/users/${id}`, { method: "DELETE" }),
  restoreUser: (id: string) => request<User>(`/api/v1/admin/users/${id}/restore`, { method: "POST" }),
  resetPassword: (id: string, password: string) =>
    request<{ message: string }>(`/api/v1/admin/users/${id}/reset-password?password=${encodeURIComponent(password)}`, {
      method: "POST",
    }),
  bulkUsers: (body: unknown) =>
    request<{ updated: number; message: string }>("/api/v1/admin/users/bulk", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  uploadPhoto: async (userId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<User>(`/api/v1/admin/users/${userId}/photo`, { method: "POST", body: fd });
  },
  idCardUrl: (id: string) => {
    const token = localStorage.getItem("token");
    return `${API_URL}/api/v1/admin/users/${id}/id-card?token=${token || ""}`;
  },
  openIdCard: (id: string) => {
    const token = localStorage.getItem("token");
    // open with auth via fetch blob
    return fetch(`${API_URL}/api/v1/admin/users/${id}/id-card`, { headers: authHeaders() })
      .then((r) => r.text())
      .then((html) => {
        const w = window.open("", "_blank");
        if (w) {
          w.document.write(html);
          w.document.close();
        }
      });
  },
  exportUsersUrl: (opts?: Record<string, string | undefined>) =>
    `${API_URL}/api/v1/admin/users/export.csv${qs(opts || {})}`,
  downloadExport: async (opts?: Record<string, string | undefined>) => {
    const res = await fetch(`${API_URL}/api/v1/admin/users/export.csv${qs(opts || {})}`, { headers: authHeaders() });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "fjsti_users.csv";
    a.click();
  },
  downloadImportTemplate: async () => {
    const res = await fetch(`${API_URL}/api/v1/admin/users/import-template.csv`, { headers: authHeaders() });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "import_template.csv";
    a.click();
  },
  importUsers: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ created: number; skipped: number; errors: string[] }>("/api/v1/admin/users/import.csv", {
      method: "POST",
      body: fd,
    });
  },
  faculties: () =>
    request<{ id: string; name: string; code?: string; departments_count?: number }[]>("/api/v1/admin/org/faculties"),
  createFaculty: (body: unknown) => request("/api/v1/admin/org/faculties", { method: "POST", body: JSON.stringify(body) }),
  updateFaculty: (id: string, body: unknown) =>
    request(`/api/v1/admin/org/faculties/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteFaculty: (id: string) => request(`/api/v1/admin/org/faculties/${id}`, { method: "DELETE" }),
  departments: (facultyId?: string) =>
    request<
      { id: string; name: string; code?: string; faculty_id?: string; faculty_name?: string; groups_count?: number; staff_count?: number }[]
    >(`/api/v1/admin/org/departments${facultyId ? `?faculty_id=${facultyId}` : ""}`),
  createDepartment: (body: unknown) =>
    request("/api/v1/admin/org/departments", { method: "POST", body: JSON.stringify(body) }),
  updateDepartment: (id: string, body: unknown) =>
    request(`/api/v1/admin/org/departments/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteDepartment: (id: string) => request(`/api/v1/admin/org/departments/${id}`, { method: "DELETE" }),
  groups: (opts?: { department_id?: string; faculty_id?: string }) =>
    request<
      {
        id: string;
        name: string;
        department_id?: string;
        department_name?: string;
        faculty_id?: string;
        faculty_name?: string;
        students_count?: number;
        academic_year?: string;
      }[]
    >(`/api/v1/admin/org/groups${qs(opts || {})}`),
  createGroup: (body: unknown) => request("/api/v1/admin/org/groups", { method: "POST", body: JSON.stringify(body) }),
  updateGroup: (id: string, body: unknown) =>
    request(`/api/v1/admin/org/groups/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteGroup: (id: string) => request(`/api/v1/admin/org/groups/${id}`, { method: "DELETE" }),
  specialties: (facultyId?: string) =>
    request<{ id: string; name: string; code?: string; faculty_id?: string; faculty_name?: string }[]>(
      `/api/v1/admin/org/specialties${facultyId ? `?faculty_id=${facultyId}` : ""}`
    ),
  createSpecialty: (body: unknown) =>
    request("/api/v1/admin/org/specialties", { method: "POST", body: JSON.stringify(body) }),
  updateSpecialty: (id: string, body: unknown) =>
    request(`/api/v1/admin/org/specialties/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteSpecialty: (id: string) => request(`/api/v1/admin/org/specialties/${id}`, { method: "DELETE" }),
  academicYears: () =>
    request<{ id: string; name: string; is_current: boolean; starts_on?: string; ends_on?: string }[]>(
      "/api/v1/admin/org/academic-years"
    ),
  createAcademicYear: (body: unknown) =>
    request("/api/v1/admin/org/academic-years", { method: "POST", body: JSON.stringify(body) }),
  updateAcademicYear: (id: string, body: unknown) =>
    request(`/api/v1/admin/org/academic-years/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteAcademicYear: (id: string) => request(`/api/v1/admin/org/academic-years/${id}`, { method: "DELETE" }),
  clients: () => request<any[]>("/api/v1/admin/clients"),
  createClient: (body: unknown) => request("/api/v1/admin/clients", { method: "POST", body: JSON.stringify(body) }),
  updateClient: (id: string, body: unknown) =>
    request(`/api/v1/admin/clients/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteClient: (id: string) => request(`/api/v1/admin/clients/${id}`, { method: "DELETE" }),
  accessLogs: (opts?: Record<string, string | number | boolean | undefined>) =>
    request<{ items: any[]; total: number; page: number; page_size: number }>(
      `/api/v1/admin/access-logs${qs(opts || {})}`
    ),
  auditLogs: (opts?: Record<string, string | number | boolean | undefined>) =>
    request<{ items: any[]; total: number; page: number; page_size: number }>(
      `/api/v1/admin/audit-logs${qs(opts || {})}`
    ),
  settings: () => request<{ key: string; value: string; label?: string }[]>("/api/v1/admin/settings"),
  saveSettings: (items: { key: string; value: string; label?: string }[]) =>
    request<{ message: string }>("/api/v1/admin/settings", { method: "PUT", body: JSON.stringify({ items }) }),
  faceRequests: (status?: string) =>
    request<{ id: string; user_id: string; user_name?: string; status: string; note?: string; created_at?: string }[]>(
      `/api/v1/users/face-update-requests${status ? `?status=${status}` : ""}`
    ),
  reviewFaceRequest: (id: string, approve: boolean) =>
    request<{ message: string }>(`/api/v1/users/face-update-requests/${id}/review?approve=${approve}`, {
      method: "POST",
    }),
  grantConsent: (userId: string) => request<{ message: string }>(`/api/v1/face/consent/${userId}`, { method: "POST" }),
  enrollFace: async (userId: string, file: File) => {
    const fd = new FormData();
    fd.append("user_id", userId);
    fd.append("file", file);
    return request<{ message: string }>("/api/v1/face/enroll", { method: "POST", body: fd });
  },
  verifyFace: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ matched: boolean; confidence?: number; user?: User; access_token?: string }>(
      "/api/v1/face/verify",
      { method: "POST", body: fd }
    );
  },
  myAccessLogs: () => request<any[]>("/api/v1/users/me/access-logs"),
  patchMe: (body: unknown) => request<User>("/api/v1/users/me", { method: "PATCH", body: JSON.stringify(body) }),
  requestFaceUpdate: (note?: string) =>
    request("/api/v1/users/me/face-update-request", { method: "POST", body: JSON.stringify({ note }) }),
};
