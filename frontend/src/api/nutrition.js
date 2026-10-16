import { request } from './foodLibrary.js'
export const getGoals = date => request('/goals?'+new URLSearchParams({date}))
export const getGoalHistory = () => request('/goals/history')
export const saveGoals = data => request('/goals', {method:'PUT',body:JSON.stringify(data)})
export const getNutrition = filters => request('/nutrition-summary?'+new URLSearchParams(filters))
export const getRecordSummary = filters => request('/record-summary?'+new URLSearchParams(Object.entries(filters).filter(([,v])=>v)))
