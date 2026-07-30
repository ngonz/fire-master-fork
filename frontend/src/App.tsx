import { Routes, Route, Navigate } from "react-router";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import SpendingPage from "./pages/SpendingPage";
import SpendingTrackerPage from "./pages/SpendingTrackerPage";
import AssetsPage from "./pages/AssetsPage";
import AccountDetailPage from "./pages/AccountDetailPage";
import RetirementPage from "./pages/RetirementPage";
import SettingsPage from "./pages/SettingsPage";
import TaxPlanningPage from "./pages/TaxPlanningPage";
import RunwayPage from "./pages/RunwayPage";
import PropertyPnLPage from "./pages/PropertyPnLPage";
import TransactionsPage from "./pages/TransactionsPage";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/spending"
        element={
          <ProtectedRoute>
            <SpendingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tracker"
        element={
          <ProtectedRoute>
            <SpendingTrackerPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/transactions"
        element={
          <ProtectedRoute>
            <TransactionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/assets"
        element={
          <ProtectedRoute>
            <AssetsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/assets/account/:id"
        element={
          <ProtectedRoute>
            <AccountDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/runway"
        element={
          <ProtectedRoute>
            <RunwayPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/properties"
        element={
          <ProtectedRoute>
            <PropertyPnLPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tax"
        element={
          <ProtectedRoute>
            <TaxPlanningPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/retirement"
        element={
          <ProtectedRoute>
            <RetirementPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      {/* Back-compat: the config form now lives under Settings → Plan */}
      <Route path="/fire/config" element={<Navigate to="/settings" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
