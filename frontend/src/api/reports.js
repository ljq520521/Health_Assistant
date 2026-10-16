import { request } from './foodLibrary.js'
export const getReport = (period,date) => request('/reports?'+new URLSearchParams({period,date}))
