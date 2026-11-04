/**
 * Pure helpers for the exercise page (member C).
 *
 * The API only returns raw records, so daily totals, weekly windows and the
 * trend series are derived here. Keeping the maths in a plain module makes it
 * testable with `node --test` and keeps ExerciseView.vue focused on layout.
 */

export const INTENSITY_LABELS = { low: '低强度', medium: '中等强度', high: '高强度' }
export const INTENSITY_OPTIONS = [
  { value: 'low', label: INTENSITY_LABELS.low },
  { value: 'medium', label: INTENSITY_LABELS.medium },
  { value: 'high', label: INTENSITY_LABELS.high },
]
export const EXERCISE_SUGGESTIONS = [
  '快走',
  '跑步',
  '骑行',
  '游泳',
  '瑜伽',
  '力量训练',
  '跳绳',
  '球类运动',
]

export const MAX_DURATION_MINUTES = 1440
export const MAX_NOTES_LENGTH = 500

const DAY_MS = 24 * 60 * 60 * 1000
const minutesOf = (record) => {
  const value = Number(record?.duration_minutes)
  return Number.isFinite(value) && value > 0 ? Math.round(value) : 0
}

export function todayInZone(timeZone = 'Asia/Shanghai') {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

/** Strict `YYYY-MM-DD` check: rejects 2026-02-30 and empty input. */
export function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  if (value.startsWith('0000')) return false
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value
}

export function shiftDate(value, days) {
  const time = Date.parse(`${value}T00:00:00Z`)
  if (!Number.isFinite(time)) throw new Error('日期不合法')
  return new Date(time + days * DAY_MS).toISOString().slice(0, 10)
}

export function formatMinutes(total) {
  const minutes = Math.max(0, Math.round(Number(total) || 0))
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
}

export function summarize(records = []) {
  const totals = new Map()
  const intensityMinutes = { low: 0, medium: 0, high: 0 }
  let totalMinutes = 0
  let longest = 0

  for (const record of records) {
    const minutes = minutesOf(record)
    totalMinutes += minutes
    longest = Math.max(longest, minutes)
    totals.set(record.record_date, (totals.get(record.record_date) || 0) + minutes)
    if (record.intensity in intensityMinutes) intensityMinutes[record.intensity] += minutes
  }

  const count = records.length
  return {
    count,
    totalMinutes,
    activeDays: totals.size,
    averageSession: count ? Math.round(totalMinutes / count) : 0,
    averagePerActiveDay: totals.size ? Math.round(totalMinutes / totals.size) : 0,
    longest,
    intensityMinutes,
  }
}

/** Newest business date first; records on the same date keep newest id first. */
export function groupByDate(records = []) {
  const groups = new Map()
  for (const record of records) {
    const date = record.record_date
    if (!groups.has(date)) groups.set(date, { date, totalMinutes: 0, count: 0, items: [] })
    const group = groups.get(date)
    group.totalMinutes += minutesOf(record)
    group.count += 1
    group.items.push(record)
  }
  return [...groups.values()]
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
    .map((group) => ({
      ...group,
      items: [...group.items].sort((a, b) => (b.id || 0) - (a.id || 0)),
    }))
}

/**
 * Zero-filled daily series for the `days` window ending at `endDate`
 * (inclusive). Days without exercise stay 0 so the chart shows real rest days.
 */
export function buildTrend(records = [], { days = 14, endDate } = {}) {
  const end = validDate(endDate) ? endDate : todayInZone()
  const totals = new Map()
  for (const record of records) {
    totals.set(record.record_date, (totals.get(record.record_date) || 0) + minutesOf(record))
  }
  const points = []
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = shiftDate(end, -offset)
    points.push({ date, minutes: totals.get(date) || 0 })
  }
  return points
}

/** `2026-10-20` -> `10-20`; used as the compact chart axis label. */
export function shortDate(value) {
  return typeof value === 'string' && value.length === 10 ? value.slice(5) : value
}

export function weekdayLabel(value) {
  if (!validDate(value)) return ''
  return new Intl.DateTimeFormat('zh-CN', { weekday: 'short', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00Z`),
  )
}
