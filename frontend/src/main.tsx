import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth";
import { AppLayout } from "./App";
import "./i18n";
import "./styles.css";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { UsersPage } from "./pages/UsersPage";
import { UserDetailPage } from "./pages/UserDetailPage";
import { FacultiesPage } from "./pages/FacultiesPage";
import { DepartmentsPage } from "./pages/DepartmentsPage";
import { GroupsPage } from "./pages/GroupsPage";
import { SpecialtiesPage } from "./pages/SpecialtiesPage";
import { AcademicYearsPage } from "./pages/AcademicYearsPage";
import { ClientsPage } from "./pages/ClientsPage";
import { LogsPage } from "./pages/LogsPage";
import { FacePage } from "./pages/FacePage";
import { PortalPage } from "./pages/PortalPage";
import { SettingsPage } from "./pages/SettingsPage";
import { FaceRequestsPage } from "./pages/FaceRequestsPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/users/:id" element={<UserDetailPage />} />
            <Route path="/faculties" element={<FacultiesPage />} />
            <Route path="/departments" element={<DepartmentsPage />} />
            <Route path="/groups" element={<GroupsPage />} />
            <Route path="/specialties" element={<SpecialtiesPage />} />
            <Route path="/years" element={<AcademicYearsPage />} />
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/face" element={<FacePage />} />
            <Route path="/face-requests" element={<FaceRequestsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/portal" element={<PortalPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>
);
