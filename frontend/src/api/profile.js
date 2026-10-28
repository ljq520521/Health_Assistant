const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const TOKEN_KEY = 'health_profile_token'

let token = ''
try {
  token = localStorage.getItem(TOKEN_KEY) || ''
} catch {
  token = ''
}

export function getToken() {
  return token
}

export function setToken(value) {
  token = value || ''
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Private mode or blocked storage: keep the in-memory token only.
  }
}

async function request(path, options = {}, withAuth = true) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 10000)
  try {
    const headers = {}
    if (options.body) headers['Content-Type'] = 'application/json'
    if (withAuth && token) headers.Authorization = `Bearer ${token}`

    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const detail = body.detail
      const first = Array.isArray(detail) ? detail[0] : null
      const message = first?.msg
        ? first.msg.replace(/^Value error, /, '')
        : detail || `请求失败（${response.status}）`
      const error = new Error(message)
      error.status = response.status
      if (response.status === 401 && withAuth) setToken('')
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

export function getSetup() {
  return request('/api/auth/setup', {}, false)
}

export function registerAccount(data) {
  return request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) })
}

export async function login(data) {
  const result = await request(
    '/api/auth/login',
    { method: 'POST', body: JSON.stringify(data) },
    false,
  )
  setToken(result.access_token)
  return result
}

export function getMe() {
  return request('/api/auth/me')
}

export async function changePassword(data) {
  const result = await request('/api/auth/password', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  setToken(result.access_token)
  return result
}

export function updatePrivacy(data) {
  return request('/api/auth/privacy', { method: 'PUT', body: JSON.stringify(data) })
}

export function listUsers() {
  return request('/api/auth/users')
}

export function setUserStatus(userId, status) {
  return request(`/api/auth/users/${userId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

export function getProfile() {
  return request('/api/profile')
}

export function saveProfile(data) {
  return request('/api/profile', { method: 'PUT', body: JSON.stringify(data) })
}

export function listGoals() {
  return request('/api/profile/goals')
}

export function createGoal(data) {
  return request('/api/profile/goals', { method: 'POST', body: JSON.stringify(data) })
}

export function updateGoal(id, data) {
  return request(`/api/profile/goals/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export function deleteGoal(id) {
  return request(`/api/profile/goals/${id}`, { method: 'DELETE' })
}

export function logout() {
  setToken('')
}
