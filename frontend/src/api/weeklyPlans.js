import { request } from './foodLibrary.js'

const post = data => ({ method: 'POST', body: JSON.stringify(data) })
export const getWeeklyContext = (startDate, goalIds = []) => request('/weekly-plan-context?' + new URLSearchParams({ start_date: startDate, selected_goal_ids: goalIds.join(',') }))
export const confirmWeeklyContext = data => request('/weekly-plan-context/confirm', post(data))
export const previewWeeklyPlan = data => request('/weekly-plans/preview', post(data))
export const saveWeeklyPlan = data => request('/weekly-plans', post(data))
export const listWeeklyPlans = (offset = 0) => request('/weekly-plans?' + new URLSearchParams({ limit: 30, offset }))
export const getWeeklyPlan = id => request(`/weekly-plans/${id}`)
export const previewWeeklyRefresh = (id, data) => request(`/weekly-plans/${id}/refresh-preview`, post(data))
export const refreshWeeklyPlan = (id, data) => request(`/weekly-plans/${id}/refresh`, post(data))
export const saveWeeklyFeedback = (id, data) => request(`/weekly-plan-items/${id}/feedback`, { method: 'PUT', body: JSON.stringify(data) })
export const getWeeklyFeedbackHistory = id => request(`/weekly-plan-items/${id}/feedback-history`)
export const getWeeklyPlanVersions = id => request(`/weekly-plans/${id}/versions`)
