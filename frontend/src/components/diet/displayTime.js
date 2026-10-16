// Display only: API timestamps and the configured IANA zone remain unchanged.
export const timeZoneLabel = zone => zone === 'Asia/Shanghai' ? '北京时间' : (zone || '时区未提供')
export function dateTimeText(value, zone) {
  if (!value) return '时间未填写'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime()) || !zone) return '时间无法显示'
  try {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('zh-CN', {
      timeZone: zone, year: 'numeric', month: 'numeric', day: 'numeric',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(date).map(p => [p.type, p.value]))
    return `${parts.year}年${parts.month}月${parts.day}日 ${parts.hour}:${parts.minute}`
  } catch { return '时间无法显示' }
}
