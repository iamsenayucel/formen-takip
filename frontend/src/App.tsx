import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--text-muted)", background: "var(--page-bg)" }}>
        Yükleniyor...
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />;
  }
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/plants" element={<ProtectedRoute><PlantsPage /></ProtectedRoute>} />
      <Route path="/plants/:plantId" element={<ProtectedRoute><PlantDetailPage /></ProtectedRoute>} />
      <Route path="/groups" element={<ProtectedRoute><GroupsPage /></ProtectedRoute>} />
      <Route path="/groups/:chiefId" element={<ProtectedRoute><GroupDetailPage /></ProtectedRoute>} />
      <Route path="/foremen" element={<ProtectedRoute><ForemenPage /></ProtectedRoute>} />
      <Route path="/foremen/:foremanId" element={<ProtectedRoute><ForemanDetailPage /></ProtectedRoute>} />
      <Route path="/foremen/:foremanId/reports/:year/:month" element={<ProtectedRoute><MonthlyForemanReportPage /></ProtectedRoute>} />
      <Route path="/kpis" element={<ProtectedRoute><KpiAnalysisPage /></ProtectedRoute>} />
      <Route path="/improvement-works" element={<ProtectedRoute><ImprovementWorksPage /></ProtectedRoute>} />
      <Route path="/improvement-works/:workId" element={<ProtectedRoute><ImprovementWorkDetailPage /></ProtectedRoute>} />
      <Route path="/anomalies" element={<ProtectedRoute><AnomaliesPage /></ProtectedRoute>} />
      <Route path="/anomalies/:anomalyId" element={<ProtectedRoute><AnomalyDetailPage /></ProtectedRoute>} />
      <Route path="/shift-analysis" element={<ProtectedRoute><ShiftAnalysisPage /></ProtectedRoute>} />
      <Route path="/shifts/:shiftId" element={<ProtectedRoute><ShiftDetailPage /></ProtectedRoute>} />
      <Route path="/executive-summary" element={<ProtectedRoute><ExecutiveSummaryPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
