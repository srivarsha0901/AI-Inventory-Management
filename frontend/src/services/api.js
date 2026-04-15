import axios from 'axios'

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
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