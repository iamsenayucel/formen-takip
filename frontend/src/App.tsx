import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { PermissionProvider, usePermissions } from "./context/PermissionContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PlantsPage } from "./pages/PlantsPage";
import { PlantDetailPage } from "./pages/PlantDetailPage";
import { GroupsPage } from "./pages/GroupsPage";
import { GroupDetailPage } from "./pages/GroupDetailPage";
import { ForemenPage } from "./pages/ForemenPage";
import { ForemanDetailPage } from "./pages/ForemanDetailPage";
import { MonthlyForemanReportPage } from "./pages/MonthlyForemanReportPage";
import { KpiAnalysisPage } from "./pages/KpiAnalysisPage";
import { ImprovementWorksPage } from "./pages/ImprovementWorksPage";
import { ImprovementWorkDetailPage } from "./pages/ImprovementWorkDetailPage";
import { AnomaliesPage } from "./pages/AnomaliesPage";
import { AnomalyDetailPage } from "./pages/AnomalyDetailPage";
import { ShiftAnalysisPage } from "./pages/ShiftAnalysisPage";
import { ShiftDetailPage } from "./pages/ShiftDetailPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ExecutiveSummaryPage } from "./pages/ExecutiveSummaryPage";
import type { Permission } from "./auth/permissions";

function ProtectedRoute({ children, permission }: { children: React.ReactNode; permission?: Permission }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const { can, isLoading: permissionsLoading } = usePermissions();

  if (isLoading || (isAuthenticated && permission && permissionsLoading)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--text-muted)", background: "var(--page-bg)" }}>
        Yükleniyor...
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />;
  }
  // Backend her endpoint'te bu kontrolü zaten tekrar yapar (authoritative source) —
  // buradaki kontrol yalnızca UX amaçlıdır: yetkisiz bir kullanıcıyı sayfa içeriğini
  // hiç render etmeden 403 ekranına yönlendirir.
  if (permission && !can(permission)) {
    return <Layout><ForbiddenPage /></Layout>;
  }
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <PermissionProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/" element={<ProtectedRoute permission="overview.view"><DashboardPage /></ProtectedRoute>} />
        <Route path="/plants" element={<ProtectedRoute permission="performance.view"><PlantsPage /></ProtectedRoute>} />
        <Route path="/plants/:plantId" element={<ProtectedRoute permission="performance.view"><PlantDetailPage /></ProtectedRoute>} />
        <Route path="/groups" element={<ProtectedRoute permission="performance.view"><GroupsPage /></ProtectedRoute>} />
        <Route path="/groups/:chiefId" element={<ProtectedRoute permission="performance.view"><GroupDetailPage /></ProtectedRoute>} />
        <Route path="/foremen" element={<ProtectedRoute permission="performance.view"><ForemenPage /></ProtectedRoute>} />
        <Route path="/foremen/:foremanId" element={<ProtectedRoute permission="performance.view"><ForemanDetailPage /></ProtectedRoute>} />
        <Route path="/foremen/:foremanId/reports/:year/:month" element={<ProtectedRoute permission="performance.view"><MonthlyForemanReportPage /></ProtectedRoute>} />
        <Route path="/kpis" element={<ProtectedRoute permission="performance.view"><KpiAnalysisPage /></ProtectedRoute>} />
        <Route path="/improvement-works" element={<ProtectedRoute permission="operational_intelligence.view"><ImprovementWorksPage /></ProtectedRoute>} />
        <Route path="/improvement-works/:workId" element={<ProtectedRoute permission="operational_intelligence.view"><ImprovementWorkDetailPage /></ProtectedRoute>} />
        <Route path="/anomalies" element={<ProtectedRoute permission="operational_intelligence.view"><AnomaliesPage /></ProtectedRoute>} />
        <Route path="/anomalies/:anomalyId" element={<ProtectedRoute permission="operational_intelligence.view"><AnomalyDetailPage /></ProtectedRoute>} />
        <Route path="/shift-analysis" element={<ProtectedRoute permission="operational_intelligence.view"><ShiftAnalysisPage /></ProtectedRoute>} />
        <Route path="/shifts/:shiftId" element={<ProtectedRoute permission="operational_intelligence.view"><ShiftDetailPage /></ProtectedRoute>} />
        <Route path="/executive-summary" element={<ProtectedRoute permission="overview.view"><ExecutiveSummaryPage /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute permission="outputs.view"><ReportsPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </PermissionProvider>
  );
}

export default App;
