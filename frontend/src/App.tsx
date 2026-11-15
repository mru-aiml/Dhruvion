import { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import AppShell from "./components/layout/AppShell";
import ProtectedRoute from "./components/layout/ProtectedRoute";
import LandingPage from "./features/landing/LandingPage";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";

// Lazy-load dashboard pages for code splitting
const OverviewPage = lazy(() => import("./features/overview/OverviewPage"));
const MissionsPage = lazy(() => import("./features/missions/MissionsPage"));
const MartianMapPage = lazy(() => import("./features/martian-map/MartianMapPage"));
const RoutePlannerPage = lazy(() => import("./features/route-planner/RoutePlannerPage"));
const ScienceExplorerPage = lazy(() => import("./features/science-explorer/ScienceExplorerPage"));
const EmergencyPage = lazy(() => import("./features/emergency/EmergencyPage"));
const AssistantPage = lazy(() => import("./features/assistant/AssistantPage"));
const ReportsPage = lazy(() => import("./features/reports/ReportsPage"));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage"));

function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={
      <div className="flex h-full items-center justify-center">
        <div className="text-text-muted">Loading…</div>
      </div>
    }>
      {children}
    </Suspense>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route
            path="/overview"
            element={
              <LazyRoute>
                <OverviewPage />
              </LazyRoute>
            }
          />
          <Route
            path="/missions"
            element={
              <LazyRoute>
                <MissionsPage />
              </LazyRoute>
            }
          />
          <Route
            path="/map"
            element={
              <LazyRoute>
                <MartianMapPage />
              </LazyRoute>
            }
          />
          <Route
            path="/routes"
            element={
              <LazyRoute>
                <RoutePlannerPage />
              </LazyRoute>
            }
          />
          <Route
            path="/science"
            element={
              <LazyRoute>
                <ScienceExplorerPage />
              </LazyRoute>
            }
          />
          <Route
            path="/emergency"
            element={
              <LazyRoute>
                <EmergencyPage />
              </LazyRoute>
            }
          />
          <Route
            path="/assistant"
            element={
              <LazyRoute>
                <AssistantPage />
              </LazyRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <LazyRoute>
                <ReportsPage />
              </LazyRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <LazyRoute>
                <SettingsPage />
              </LazyRoute>
            }
          />
        </Route>
      </Routes>
    </AuthProvider>
  );
}