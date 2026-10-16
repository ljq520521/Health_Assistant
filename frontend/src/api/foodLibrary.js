const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const labels = { name: '名称', category_id: '分类', calories_per_100g: '热量', protein_g_per_100g: '蛋白质', fat_g_per_100g: '脂肪', carbohydrate_g_per_100g: '碳水化合物', source_type: '来源类型', source_note: '来源说明', source_url: '来源链接' }
export async function request(path, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 10000)
  try {
    const response = await fetch(`${baseUrl}/api/diet${path}`, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json' } })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const message = Array.isArray(body.detail) ? body.detail.map(item => `${labels[item.loc?.at(-1)] || '输入'}不合法，请检查必填项和来源信息`).join('；') : body.detail || `请求失败（${response.status}）`
      const error = new Error(message)
      error.status = response.status
      error.code = body.code
      throw error
    }
    return response.status === 204 ? null : response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请重试')
    if (error instanceof TypeError) throw new Error('无法连接后端，请检查服务后重试')
    throw error
  } finally { clearTimeout(timer) }
}
const body = (method, data) => ({ method, body: JSON.stringify(data) })
export const getDietConfig = () => request('/config')
export const listCategories = () => request('/food-categories')
export const createCategory = data => request('/food-categories', body('POST', data))
export const updateCategory = (id, data) => request(`/food-categories/${id}`, body('PUT', data))
export const deleteCategory = id => request(`/food-categories/${id}`, { method: 'DELETE' })
export function listFoods(filters = {}) {
  const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== '' && value != null && value !== false))
  return request(`/foods${query.size ? '?' + query : ''}`)
}
export const createFood = data => request('/foods', body('POST', data))
export const updateFood = (id, data) => request(`/foods/${id}`, body('PUT', data))
export const archiveFood = id => request(`/foods/${id}`, { method: 'DELETE' })
