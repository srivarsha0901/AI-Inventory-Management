import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider }   from './context/AuthContext'
import ProtectedRoute     from './components/layout/ProtectedRoute'
import AppLayout          from './components/layout/AppLayout'
import LoginPage          from './pages/LoginPage'
import RegisterPage       from './pages/RegisterPage'
import OnboardingPage     from './pages/OnboardingPage'
import DashboardPage      from './pages/DashboardPage'
import POSPage            from './pages/POSPage'
import InventoryPage      from './pages/InventoryPage'
import ForecastPage       from './pages/ForecastPage'
import ReorderPage        from './pages/ReorderPage'
import OCRPage            from './pages/OCRPage'
import { AlertsPage }     from './pages/AlertsPage'
import AnalyticsPage      from './pages/AnalyticsPage'
import TransactionsPage   from './pages/TransactionsPage'
import OnboardingGuard    from './components/ui/OnboardingGuard'
import StaffPage          from './pages/StaffPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login"       element={<LoginPage />} />
        <Route path="/register"    element={<RegisterPage />} />
        <Route path="/onboarding"  element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/upload-sales" element={<ProtectedRoute><OnboardingPage startStep={3} /></ProtectedRoute>} />
        <Route path="/"            element={<Navigate to="/login" replace />} />

        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><DashboardPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><AnalyticsPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/inventory" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><InventoryPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/alerts" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><AlertsPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/ocr" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><OCRPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/forecast" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><ForecastPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/reorder" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><ReorderPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/pos" element={
            <ProtectedRoute allowedRoles={['cashier','manager']}>
              <OnboardingGuard><POSPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/staff" element={
            <ProtectedRoute allowedRoles={['manager']}>
              <OnboardingGuard><StaffPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
          <Route path="/transactions" element={
            <ProtectedRoute allowedRoles={['cashier','manager']}>
              <OnboardingGuard><TransactionsPage /></OnboardingGuard>
            </ProtectedRoute>
          } />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  )
}