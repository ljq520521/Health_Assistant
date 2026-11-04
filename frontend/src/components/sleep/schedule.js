// Weekdays belong to the planned bedtime/alarm date, even when an alert is earlier.
export function dueEvents(settings, previous, now) {
  if (!settings || now < previous) return []
  const day = new Date(now + 8 * 3600000).toISOString().slice(0, 10)
  const events = []
  const minute = value => Number(value.slice(0, 2)) * 60 + Number(value.slice(3))
  for (const offset of [-1, 0, 1]) {
    const stamp = Date.parse(`${day}T12:00:00+08:00`) + offset * 86400000
    const date = new Date(stamp + 8 * 3600000).toISOString().slice(0, 10)
    const weekday = (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7
    if (!settings.weekdays.includes(weekday)) continue
    const alarmAdvance = (minute(settings.alarm_time) - minute(settings.effective_alarm_time) + 1440) % 1440
    const candidates = [
      { kind: 'bedtime', enabled: settings.bedtime_enabled, at: Date.parse(`${date}T${settings.bedtime}:00+08:00`) - settings.reminder_minutes * 60000, title: '准备休息了', message: `计划 ${settings.bedtime} 入睡，可以开始睡前准备。` },
      { kind: 'alarm', enabled: settings.alarm_enabled, at: Date.parse(`${date}T${settings.alarm_time}:00+08:00`) - alarmAdvance * 60000, title: '早安，到起床时间了', message: `今天的唤醒时间是 ${settings.effective_alarm_time}。` },
    ]
    for (const event of candidates) if (event.enabled && event.at > Math.max(previous, now - 90000) && event.at <= now) events.push({ ...event, id: `${event.kind}-${date}` })
  }
  return events.sort((a, b) => a.at - b.at)
}
