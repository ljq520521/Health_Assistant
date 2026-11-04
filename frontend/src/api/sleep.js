import { getToken, setToken } from './profile.js'

export const apiBase = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')

function accessError(message, status, token) {
  const error = new Error(message)
  error.status = status
  if (token === getToken()) {
    if (status === 401) setToken('')
    if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('sleep-access-denied', { detail: { message, status } }))
  }
  return error
}

export async function request(path, options = {}) {
  const token = getToken()
  if (!token) throw accessError('请先在健康档案页面登录', 401, token)
  const { responseType = 'json', ...fetchOptions } = options
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.body instanceof Blob ? 60000 : 10000)
  try {
    const response = await fetch(`${apiBase}/api${path}`, {
      ...fetchOptions, signal: controller.signal, cache: 'no-store',
      headers: { ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}), ...options.headers, Authorization: `Bearer ${token}` },
    })
    if (token !== getToken()) throw accessError('登录状态已改变，请重新加载', 401, token)
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('；') : data.detail
      if ([401, 403].includes(response.status)) throw accessError(detail || '没有访问权限', response.status, token)
      const error = new Error(detail || `请求失败（${response.status}）`)
      error.status = response.status
      throw error
    }
    const result = response.status === 204 ? null : await (responseType === 'blob' ? response.blob() : response.json())
    if (token !== getToken()) throw accessError('登录状态已改变，请重新加载', 401, token)
    return result
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请检查连接后重试')
    throw error
  } finally { clearTimeout(timeout) }
}

export const json = (method, value) => ({ method, body: JSON.stringify(value) })

export function shanghaiInput(value = new Date()) {
  return new Date(new Date(value).getTime() + 8 * 3600000).toISOString().slice(0, 16)
}

export const today = () => shanghaiInput().slice(0, 10)
export const hours = value => value == null ? '—' : `${(value / 60).toFixed(1)} 小时`
export const displayTime = value => shanghaiInput(value).replace('T', ' ')

export async function downloadReport(period, endDate) {
  const blob = await request(`/sleep/report?${new URLSearchParams({ period, end_date: endDate, format: 'csv' })}`, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `睡眠报告-${endDate}-${period}.csv`
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
