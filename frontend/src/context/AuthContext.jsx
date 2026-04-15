import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'

const AuthContext = createContext(null)

// Helper to decode JWT and get expiry time
function decodeToken(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const decoded = JSON.parse(atob(parts[1]))
    return decoded
  } catch {
    return null
  }
}

// Helper to check if token is expired
function isTokenExpired(token) {
  const decoded = decodeToken(token)
  if (!decoded || !decoded.exp) return true
  return Math.floor(Date.now() / 1000) >= decoded.exp
}

// Helper to get time until expiry
function getTimeUntilExpiry(token) {
  const decoded = decodeToken(token)
  if (!decoded || !decoded.exp) return 0
  return (decoded.exp - Math.floor(Date.now() / 1000)) * 1000 // milliseconds
}

export function AuthProvider({ children }) {
  const [user, setUser]             = useState(null)
  const [token, setToken]           = useState(null)
  const [loading, setLoading]       = useState(true)
  const [isRefreshing, setRefreshing] = useState(false)
  const pendingRequests = useRef([])
  const refreshTimer = useRef(null)

  // Load from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('ft_token')
    const savedUser = localStorage.getItem('ft_user')
    
    if (savedToken && savedUser) {
      try {
        setToken(savedToken)
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem('ft_token')
        localStorage.removeItem('ft_user')
      }
    }
    setLoading(false)
  }, [])

  // Set up auto-refresh timer
  useEffect(() => {
    if (!token || isRefreshing) return

    // Calculate time until refresh (1 hour before expiry)
    const timeUntilExpiry = getTimeUntilExpiry(token)
    const refreshDelay = Math.max(0, timeUntilExpiry - (60 * 60 * 1000)) // Refresh 1 hour before

    if (refreshDelay <= 0) {
      // Token expires within 1 hour, refresh immediately
      refreshToken()
      return
    }

    // Schedule refresh
    refreshTimer.current = setTimeout(refreshToken, refreshDelay)

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current)
    }
  }, [token, isRefreshing])

  const refreshToken = useCallback(async () => {
    if (isRefreshing || !token) return

    setRefreshing(true)

    try {
      const response = await fetch('http://127.0.0.1:5000/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        // 401 - token invalid, logout user
        if (response.status === 401) {
          logout()
        }
        throw new Error('Token refresh failed')
      }

      const data = await response.json()
      const newToken = data.token
      const newUser = data.user

      // Update state
      setToken(newToken)
      setUser(newUser)

      // Update localStorage
      localStorage.setItem('ft_token', newToken)
      localStorage.setItem('ft_user', JSON.stringify(newUser))

      // Resolve pending requests with new token
      while (pendingRequests.current.length > 0) {
        const { resolve } = pendingRequests.current.shift()
        resolve(newToken)
      }
      return newToken
    } catch (error) {
      console.error('Token refresh error:', error)
      // On error, queue pending requests with old token (they'll likely fail, but give API a chance)
      while (pendingRequests.current.length > 0) {
        const { resolve } = pendingRequests.current.shift()
        resolve(token)
      }
      return token
    } finally {
      setRefreshing(false)
    }
  }, [token, isRefreshing])

  const login = (userData, authToken) => {
    const resolvedToken = authToken || userData?.token || null
    const { token: _embeddedToken, ...safeUser } = userData || {}
    setUser(safeUser)
    setToken(resolvedToken)
    if (resolvedToken) localStorage.setItem('ft_token', resolvedToken)
    localStorage.setItem('ft_user', JSON.stringify(safeUser))
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('ft_token')
    localStorage.removeItem('ft_user')
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
  }

  // Get token for API requests (handles refresh if needed)
  const getToken = useCallback(async () => {
    if (!token) return null

    if (isTokenExpired(token)) {
      // Token expired, refresh it
      if (!isRefreshing) {
        return await refreshToken()
      } else {
        // Refresh in progress, queue this request
        return new Promise((resolve) => {
          pendingRequests.current.push({ resolve })
        })
      }
    }

    return token
  }, [token, isRefreshing, refreshToken])

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, getToken, isRefreshing }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)