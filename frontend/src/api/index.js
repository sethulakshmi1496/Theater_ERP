import api from './client';

export const authAPI = {
  login: (email, password) => api.post('/auth/login/', { email, password }),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  me: () => api.get('/accounts/me/'),
  users: () => api.get('/accounts/users/'),
};

export const screensAPI = {
  list: () => api.get('/screens/screens/'),
  create: (data) => api.post('/screens/screens/', data),
  delete: (id) => api.delete(`/screens/screens/${id}/`),
  configureSeats: (id, data) => api.post(`/screens/screens/${id}/configure-seats/`, data),
  shows: (params) => api.get('/screens/shows/', { params }),
  showSeatMap: (showId) => api.get(`/screens/shows/${showId}/seat-map/`),
  movies: (id) => id ? api.get(`/screens/movies/${id}/`) : api.get('/screens/movies/'),
  createShow: (data) => api.post('/screens/shows/', data),
  createMovie: (data) => api.post('/screens/movies/', data),
  updateMovie: (id, data) => api.patch(`/screens/movies/${id}/`, data),
  deleteMovie: (id) => api.delete(`/screens/movies/${id}/`),
  deleteShow: (id) => api.delete(`/screens/shows/${id}/`),
};

export const bookingsAPI = {
  list: (params) => api.get('/bookings/', { params }),
  create: (data) => api.post('/bookings/', data),
  cancel: (id) => api.post(`/bookings/${id}/cancel/`),
  bmsSyncLogs: () => api.get('/bookings/bms-sync-logs/'),
  triggerBmsSync: () => api.post('/bookings/trigger-bms-sync/'),
};

export const operationsAPI = {
  utilityMeters: {
    list: (params) => api.get('/operations/utility-meters/', { params }),
  },
  utilityConfigs: {
    list: (params) => api.get('/operations/utility-configs/', { params }),
  },
  utilityReadings: {
    list: (params) => api.get('/operations/utility-readings/', { params }),
    create: (data) => api.post('/operations/utility-readings/', data),
    update: (id, data) => api.put(`/operations/utility-readings/${id}/`, data),
    predictiveDefaults: () => api.get('/operations/utility-readings/predictive-defaults/'),
  },
  generator: {
    list: (params) => api.get('/operations/generator/', { params }),
    create: (data) => api.post('/operations/generator/', data),
  },
  lamps: {
    list: (params) => api.get('/operations/lamps/', { params }),
    create: (data) => api.post('/operations/lamps/', data),
    delete: (id) => api.delete(`/operations/lamps/${id}/`),
    predictiveDefaults: () => api.get('/operations/lamps/predictive-defaults/'),
  },
  lampInventory: {
    list: (params) => api.get('/operations/lamp-inventory/', { params }),
    create: (data) => api.post('/operations/lamp-inventory/', data),
    update: (id, data) => api.patch(`/operations/lamp-inventory/${id}/`, data),
    history: (id) => api.get(`/operations/lamp-inventory/${id}/history/`),
  },
  assetCategories: {
    list: (params) => api.get('/operations/asset-categories/', { params }),
  },
  assetTemplates: {
    list: (params) => api.get('/operations/asset-templates/', { params }),
    create: (data) => api.post('/operations/asset-templates/', data),
  },
  tenantAssets: {
    list: (params) => api.get('/operations/tenant-assets/', { params }),
    create: (data) => api.post('/operations/tenant-assets/', data),
    update: (id, data) => api.patch(`/operations/tenant-assets/${id}/`, data),
    alerts: () => api.get('/operations/tenant-assets/alerts/'),
  },
  assetLogs: {
    list: (params) => api.get('/operations/asset-logs/', { params }),
    create: (data) => api.post('/operations/asset-logs/', data),
  },
};

export const revenueAPI = {
  cafeUnits: () => api.get('/revenue/canteen/units/'),
  createCafeUnit: (data) => api.post('/revenue/canteen/units/', data),
  canteenItems: () => api.get('/revenue/canteen/items/'),
  canteenSales: (params) => api.get('/revenue/canteen/sales/', { params }),
  createCanteenSale: (data) => api.post('/revenue/canteen/sales/', data),
  cafeExpenses: (params) => api.get('/revenue/canteen/expenses/', { params }),
  createCafeExpense: (data) => api.post('/revenue/canteen/expenses/', data),
  adSlots: (params) => api.get('/revenue/advertising/', { params }),
  createAdSlot: (data) => api.post('/revenue/advertising/', data),
};

export const financeAPI = {
  advances: () => api.get('/finance/advances/'),
  createAdvance: (data) => api.post('/finance/advances/', data),
  distributorShare: () => api.get('/finance/distributor-share/'),
  createDistributorShare: (data) => api.post('/finance/distributor-share/', data),
};

export const payrollAPI = {
  staff: () => api.get('/payroll/staff/'),
  createStaff: (data) => api.post('/payroll/staff/', data),
};

export const reportsAPI = {
  dailyPL: (date) => api.get('/reports/pl/daily/', { params: { date } }),
  monthlyPL: (month, year) => api.get('/reports/pl/monthly/', { params: { month, year } }),
  alerts: () => api.get('/reports/alerts/'),
  exportDailyCSV: (date) => `${import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/reports/export/daily/?date=${date}`,
  exportMonthlyCSV: (month, year) => `${import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/reports/export/monthly/?month=${month}&year=${year}`,
};

export const settingsAPI = {
  profile: () => api.get('/settings/profile/'),
  updateProfile: (id, data) => api.patch(`/settings/profile/${id}/`, data),
  modules: () => api.get('/settings/modules/'),
  updateModule: (id, data) => api.patch(`/settings/modules/${id}/`, data),
  keys: () => api.get('/settings/keys/'),
  updateKey: (id, data) => api.patch(`/settings/keys/${id}/`, data),
  createKey: (data) => api.post('/settings/keys/', data),
};

export const auditAPI = {
  deletedLogs: (params) => api.get('/audit/deleted-logs/', { params }),
  changeLogs: (params) => api.get('/audit/change-logs/', { params }),
  staffSessions: (params) => api.get('/audit/staff-sessions/', { params }),
  checkIn: () => api.post('/audit/staff-sessions/'),
  checkOut: (id) => api.post(`/audit/staff-sessions/${id}/check-out/`),
  verifyDelete: (password) => api.post('/audit/delete-verify/verify/', { password }),
};

export const integrationsAPI = {
  dcrList: (params) => api.get('/integrations/dcr/', { params }),
  dcrUpload: (formData) => api.post('/integrations/dcr/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  dcrApprove: (id) => api.post(`/integrations/dcr/${id}/approve/`),
  dcrPost: (id) => api.post(`/integrations/dcr/${id}/post_to_finance/`),
};
