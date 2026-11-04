// Presentation only: never rewrite the API object or infer approval from import metadata.
import { isApprovedRecord, COURSE_APPROVAL_NOTICE } from './demoContext.js'
export const sourceLabels = { user_entered: '用户录入', referenced: '参考资料', example: '示例数据' }

export function httpsSourceUrl(value) {
  if (typeof value !== 'string' || !/^https:\/\//i.test(value.trim()) || /[\s\\]/.test(value.trim())) return ''
  try {
    const url = new URL(value.trim())
    return url.protocol === 'https:' && url.hostname && !url.username && !url.password ? url.href : ''
  } catch { return '' }
}

export function foodSource(food, demo = null) {
  const note = typeof food.source_note === 'string' ? food.source_note : ''
  // Only the human-readable prefix is evidence for display; never render the JSON tail.
  const prefix = note.split(/HAIMPORT1\s*:/i)[0]
  const human = prefix.split(/[\r\n]/).filter(line => !/[{}\[\]]|content_sha256|run_id|\bkey\s*[:=]/i.test(line)).join(' ').trim()
  const href = httpsSourceUrl(food.source_url)
  const usda = food.source_type === 'referenced' && (
    (href && new URL(href).hostname === 'fdc.nal.usda.gov') || /\bUSDA FoodData Central\b/i.test(human)
  )
  const imported = /HAIMPORT1\s*:/i.test(note)
  const verified = /来源数据已技术核验|已核验来源/.test(human)
  const pending = /尚未获得团队正式批准|待团队正式审核|待审核|temporary_review|pending_final_confirmation/.test(human)
  return {
    label: usda ? '数据来源：USDA FoodData Central' : (human || href)
      ? `数据来源：${sourceLabels[food.source_type] || '其他资料'}` : '来源未填写',
    // A marker identifies an import, not its review or verification status.
    review: (food.origin === 'public' && food.editable === false && food.food_key) || isApprovedRecord(food, 'food', demo) ? `${COURSE_APPROVAL_NOTICE}；食品来源已技术核验；成分与过敏原未完整核验。`
      : verified && pending ? '已核验来源，待团队正式审核' : imported || pending ? '审核状态未确认，请核对来源' : '',
    href,
  }
}

export function nutrientDisplay(value) {
  const known = typeof value === 'number' && Number.isFinite(value) && value >= 0
  return { known, text: known ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 }).format(value) : '未知' }
}
