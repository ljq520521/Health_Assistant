export const feedbackStates = Object.freeze({
  pending: { label: '未反馈', icon: '○', tone: 'neutral' },
  completed: { label: '已完成', icon: '✓', tone: 'success' },
  not_completed: { label: '未完成', icon: '×', tone: 'danger' },
  partial: { label: '部分完成', icon: '◐', tone: 'partial' },
  not_applicable: { label: '不适用', icon: '—', tone: 'neutral' },
})
export const mealLabels = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }
export const feedbackState = status => feedbackStates[status] || { label: '状态未知', icon: '?', tone: 'neutral' }
export const formatPercent = value => value == null ? '暂无可统计事项' : `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(value)}%`
export const messageText = value => typeof value === 'string' ? value : value?.message || value?.detail || value?.reason || value?.code || '请完善相关资料'
export function groupPlanDays(items = []) {
  const days = new Map()
  for (const item of items) {
    if (!days.has(item.date)) days.set(item.date, [])
    days.get(item.date).push(item)
  }
  return [...days].sort(([a], [b]) => a.localeCompare(b)).map(([date, entries]) => ({ date, items: entries.sort((a, b) => Object.keys(mealLabels).indexOf(a.meal_type) - Object.keys(mealLabels).indexOf(b.meal_type)) }))
}
// An invalidated response must never replace newer conditions or a disposed page.
export function createLatestRequest() {
  let revision = 0
  return {
    begin: () => ++revision,
    current: token => token === revision,
    invalidate: () => { revision += 1 },
  }
}
export function feedbackChoices(item) {
  return Object.entries(feedbackStates).filter(([status]) => item.recipe || ['pending', 'not_applicable'].includes(status))
}
export function buildWeeklyInput(form, contextHash) {
  return {
    start_date: form.start_date,
    portions: Number(form.portions),
    meal_ratios: Object.fromEntries(Object.keys(mealLabels).map(meal => [meal, form.ratios[meal] === '' || form.ratios[meal] == null ? null : Number(form.ratios[meal]) / 100])),
    selected_goal_ids: [...form.selected_goal_ids],
    expected_context_hash: contextHash,
  }
}

// Focus/visibility events inside the throttle window must trigger a trailing read.
// A pending read also survives a mutation; resume() runs when that action settles.
export function createLifecycleRefresh({ getLastRefresh, isBusy, isVisible, refresh, now = Date.now, schedule = setTimeout, cancel = clearTimeout, throttleMs = 1500 }) {
  let pending = false, timer = null, disposed = false
  function flush() {
    timer = null
    if (disposed || !pending || !isVisible() || isBusy()) return
    const remaining = throttleMs - (now() - getLastRefresh())
    if (remaining > 0) { timer = schedule(flush, remaining); return }
    pending = false
    refresh()
  }
  return {
    request() { if (disposed || !isVisible()) return; pending = true; if (timer !== null) cancel(timer); flush() },
    resume() { if (pending && !disposed) { if (timer !== null) cancel(timer); flush() } },
    dispose() { disposed = true; pending = false; if (timer !== null) cancel(timer) },
  }
}
