import api from './api'

export const authService = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  logout:   ()     => api.post('/auth/logout'),
  me:       ()     => api.get('/auth/me'),
}
export const mlService = {
  runPredictions: () => api.post('/ml/run-predictions'),
}
export const staffService = {
  getAll:       ()         => api.get('/staff'),
  create:       (data)     => api.post('/staff', data),
  deactivate:   (id)       => api.post(`/staff/${id}/deactivate`),
  getSales:     (id)       => api.get(`/staff/${id}/sales`),
  getActivity:  (params)   => api.get('/activity', { params }),
}

export const inventoryService = {
  getAll:    (params) => api.get('/inventory', { params }),
  getById:   (id)     => api.get(`/inventory/${id}`),
  create:    (data)   => api.post('/inventory', data),
  update:    (id, d)  => api.put(`/inventory/${id}`, d),
  delete:    (id)     => api.delete(`/inventory/${id}`),
  getLow:    ()       => api.get('/inventory/low-stock'),
  getExpiry: ()       => api.get('/inventory/expiring'),
}

export const posService = {
  getProducts:    ()  => api.get('/products'),
  searchProducts: (q) => api.get('/products/search', { params: { q } }),
  createSale:     (data) => api.post('/sales', data),
  getSales:       (p)    => api.get('/sales', { params: p }),
  getSaleById:    (id)   => api.get(`/sales/${id}`),
}

export const dashboardService = {
  getStats:       ()       => api.get('/dashboard/stats'),
  getSalesTrend:  (period) => api.get('/dashboard/sales-trend', { params: { period } }),
  getTopProducts: ()       => api.get('/dashboard/top-products'),
  getAlerts:      ()       => api.get('/dashboard/alerts'),
}

export const forecastService = {
  getForecasts:  (params) => api.get('/forecast', { params }),
  runForecast:   (data)   => api.post('/ml/run-predictions', data),
  getAccuracy:   ()       => api.get('/forecast/accuracy'),
  getComparison: (params) => api.get('/forecast/comparison', { params }),
}

export const reorderService = {
  getSuggestions: ()     => api.get('/reorder/suggestions'),
  approve:        (id)   => api.post(`/reorder/${id}/approve`),
  dismiss:        (id)   => api.post(`/reorder/${id}/dismiss`),
  getSettings:    ()     => api.get('/reorder/settings'),
  updateSettings: (data) => api.put('/reorder/settings', data),
}

export const ocrService = {
  uploadInvoice: (formData) => api.post('/ocr/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getExtracted:  (id)       => api.get(`/ocr/${id}`),
  confirmItems:  (id, d)    => api.post(`/ocr/${id}/confirm`, d),
  getHistory:    ()         => api.get('/ocr/history'),
}

export const alertService = {
  getAll:     ()   => api.get('/alerts'),
  dismiss:    (id) => api.post(`/alerts/${id}/dismiss`),
  resolve:    (id) => api.post(`/alerts/${id}/resolve`),
  dismissAll: ()   => api.patch('/alerts/dismiss-all'),
}

export const seasonalService = {
  getUpcoming:      ()       => api.get('/seasonal/upcoming'),
  applyBoost:       (data)   => api.post('/seasonal/apply-boost', data),
  getSuggestions:   (region) => api.get('/seasonal/suggestions', { params: { region } }),
  getNotifications: ()       => api.get('/seasonal/notifications'),
}
