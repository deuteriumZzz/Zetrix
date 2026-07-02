import axios from 'axios'
import { useAuthStore } from '../store/auth'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const orig = err.config
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true
      const refresh = useAuthStore.getState().refreshToken
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/token/refresh/', { refresh })
          useAuthStore.getState().setTokens(data.access, refresh)
          orig.headers.Authorization = `Bearer ${data.access}`
          return api(orig)
        } catch {
          useAuthStore.getState().clearTokens()
        }
      }
    }
    return Promise.reject(err)
  },
)

export default api
