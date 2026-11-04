import test from 'node:test'
import assert from 'node:assert/strict'
import { dueEvents } from '../src/components/sleep/schedule.js'

const settings = { bedtime: '23:00', alarm_time: '07:00', effective_alarm_time: '06:30', reminder_minutes: 30, bedtime_enabled: true, alarm_enabled: true, weekdays: [0,1,2,3,4,5,6] }
const at = value => Date.parse(value + '+08:00')

test('alarm triggers at estimated time once per interval', () => {
  const now = at('2026-09-21T06:30:00')
  const events = dueEvents(settings, now - 1000, now)
  assert.equal(events.length, 1); assert.equal(events[0].kind, 'alarm')
  assert.deepEqual(dueEvents(settings, now, now + 1000), [])
})
test('reminders before midnight use the planned bedtime weekday', () => {
  const now = at('2026-09-20T23:40:00') // Sunday night, Monday bedtime.
  const events = dueEvents({ ...settings, bedtime: '00:10', weekdays: [0] }, now - 1000, now)
  assert.equal(events.length, 1); assert.equal(events[0].id, 'bedtime-2026-09-21')
})
test('smart alarm before midnight belongs to intended wake day', () => {
  const now = at('2026-09-20T23:40:00')
  const events = dueEvents({ ...settings, alarm_time: '00:00', effective_alarm_time: '23:40', weekdays: [0] }, now - 1000, now)
  assert.equal(events[0].id, 'alarm-2026-09-21')
})
test('disabled days and stale events after suspension are skipped', () => {
  const now = at('2026-09-21T06:30:00')
  assert.deepEqual(dueEvents({ ...settings, weekdays: [6] }, now - 1000, now), [])
  assert.deepEqual(dueEvents({ ...settings, alarm_enabled: false }, now - 1000, now), [])
  assert.deepEqual(dueEvents(settings, now - 1000, now + 300000), [])
})
