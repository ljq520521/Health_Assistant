const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const fieldLabels = {
  record_date: '日期',
  exercise_type: '运动类型',
  duration_minutes: '时长',
  intensity: '强度',
  notes: '备注',
  date_from: '开始日期',
  date_to: '结束日期',
}

async function request(path = '', options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 10000)
  try {
    const response = await fetch(`${baseUrl}/api/exercise-records${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const detail = body.detail
      const message = Array.isArray(detail)
        ? detail.map((item) => `${fieldLabels[item.loc?.at(-1)] || '参数'}不合法`).join('；')
        : detail || `请求失败（${response.status}）`
      const error = new Error(message)
      error.status = response.status
      error.code = body.code
      throw error
    }
    return response.status === 204 ? null : response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请重试')
    if (error instanceof TypeError) throw new Error('无法连接服务，请检查后端后重试')
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

export function listExercise(filters = {}) {
  const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value))
  return request(query.size ? `?${query}` : '')
}

export const getExercise = (id) => request(`/${id}`)

export const createExercise = (data) =>
  request('', { method: 'POST', body: JSON.stringify(data) })

export const updateExercise = (id, data) =>
  request(`/${id}`, { method: 'PUT', body: JSON.stringify(data) })

export const deleteExercise = (id) => request(`/${id}`, { method: 'DELETE' })
