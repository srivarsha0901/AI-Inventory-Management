import axios from 'axios'

// Use relative /api in dev (Vite proxies to Flask). Override with VITE_API_BASE_URL in production.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const tokenFromStorage = localStorage.getItem('ft_token')
  if (tokenFromStorage) {
    config.headers.Authorization = `Bearer ${tokenFromStorage}`
    return config
  }

  const saved = localStorage.getItem('ft_user')
  if (saved) {
    const { token } = JSON.parse(saved)
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ft_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api