import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Navbar from './components/Navbar'
import PrivateRoute from './components/PrivateRoute'
import Dashboard from './pages/Dashboard'
import CountryDetail from './pages/CountryDetail'
import Reports from './pages/Reports'
import Subscriptions from './pages/Subscriptions'
import Login from './pages/Login'

export default function App() {
  const token = useAuthStore((s) => s.accessToken)

  return (
    <BrowserRouter>
      {token && <Navbar />}
      <Routes>
        <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />
        <Route element={<PrivateRoute />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/countries/:iso2" element={<CountryDetail />} />
          <Route path="/countries/:iso2/regions/:regionId" element={<CountryDetail />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
