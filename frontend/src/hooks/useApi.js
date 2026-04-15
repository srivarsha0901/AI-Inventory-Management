import { useState, useEffect, useCallback } from 'react'

export function useApi(apiFn, params = null, deps = []) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const fetch = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const res = await (params ? apiFn(params) : apiFn())
      setData(res.data)
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Something went wrong')
    } finally { setLoading(false) }
  }, deps) // eslint-disable-line

  useEffect(() => { fetch() }, [fetch])
  return { data, loading, error, refetch: fetch }
}