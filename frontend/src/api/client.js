const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function getHealth() {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(`${baseUrl}/health`, { signal: controller.signal })
    if (!response.ok) throw new Error(`服务返回 ${response.status}`)
    const body = await response.json()
    if (body.status !== 'ok' || body.database !== 'ok') throw new Error('服务状态异常')
    return body
  } finally {
    clearTimeout(timeout)
  }
}
