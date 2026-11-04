export const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.body instanceof Blob ? 60000 : 10000)
  try {
    const response = await fetch(`${apiBase}/api${path}`, {
      ...options, signal: controller.signal,
      headers: { ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('；') : data.detail
      throw new Error(detail || `请求失败（${response.status}）`)
    }
    return response.status === 204 ? null : response.json()
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
  const response = await fetch(`${apiBase}/api/sleep/report?${new URLSearchParams({ period, end_date: endDate, format: 'csv' })}`, { signal: AbortSignal.timeout(10000) })
  if (!response.ok) throw new Error('报告下载失败，请稍后重试')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `睡眠报告-${endDate}-${period}.csv`
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
