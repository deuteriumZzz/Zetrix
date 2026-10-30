import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import ErrorBoundary from './components/ErrorBoundary'
import PrivateRoute from './components/PrivateRoute'
import LandingPage from './pages/LandingPage'
import CountryDetail from './pages/CountryDetail'
import Reports from './pages/Reports'
import Subscriptions from './pages/Subscriptions'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Terms from './pages/Terms'
import Privacy from './pages/Privacy'
import Pricing from './pages/Pricing'

export default function App() {
  const token = useAuthStore((s) => s.accessToken)

  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Navbar />
        <Routes>
          <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />
          <Route path="/register" element={token ? <Navigate to="/" replace /> : <Register />} />
          <Route path="/forgot-password" element={token ? <Navigate to="/" replace /> : <ForgotPassword />} />
          <Route path="/reset-password" element={token ? <Navigate to="/" replace /> : <ResetPassword />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/" element={<LandingPage />} />
          <Route path="/countries/:iso2" element={<CountryDetail />} />
          <Route path="/countries/:iso2/regions/:regionId" element={<CountryDetail />} />
          <Route element={<PrivateRoute />}>
            <Route path="/reports" element={<Reports />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </ErrorBoundary>
    </BrowserRouter>
  )
}
