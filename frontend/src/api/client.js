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
export async function getCycleRecords() {
  const response = await fetch(`${baseUrl}/api/cycle-records`)
  if (!response.ok) throw new Error(`服务返回 ${response.status}`)
  return response.json()
}

export async function createCycleRecord(data) {
  const response = await fetch(`${baseUrl}/api/cycle-records`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error(`服务返回 ${response.status}`)
  return response.json()
}

export async function deleteCycleRecord(id) {
  const response = await fetch(`${baseUrl}/api/cycle-records/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error(`服务返回 ${response.status}`)
  return response.json()
}

export async function getCyclePrediction() {
  const response = await fetch(`${baseUrl}/api/cycle-records/predict`)
  if (!response.ok) throw new Error(`服务返回 ${response.status}`)
  return response.json()
}
