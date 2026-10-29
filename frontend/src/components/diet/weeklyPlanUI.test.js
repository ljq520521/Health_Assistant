import test from 'node:test'
import assert from 'node:assert/strict'
import { buildWeeklyInput, createLatestRequest, createLifecycleRefresh, feedbackChoices, feedbackState, feedbackStates, formatPercent, groupPlanDays, messageText } from './weeklyPlanUI.js'

test('all five feedback states carry distinct text/icons and accessible semantic color groups', () => {
  assert.deepEqual(Object.keys(feedbackStates), ['pending', 'completed', 'not_completed', 'partial', 'not_applicable'])
  assert.equal(feedbackState('completed').tone, 'success')
  assert.equal(feedbackState('not_completed').tone, 'danger')
  assert.equal(feedbackState('pending').tone, 'neutral')
  assert.equal(feedbackState('partial').tone, 'partial')
  assert.equal(new Set(Object.values(feedbackStates).map(item => item.label)).size, 5)
  assert.equal(feedbackState('unexpected').label, '状态未知')
})
test('no candidate can be left pending or inapplicable, never forced into execution failure', () => {
  assert.deepEqual(feedbackChoices({ recipe: null }).map(([key]) => key), ['pending', 'not_applicable'])
  assert.equal(feedbackChoices({ recipe: { name: '有来源的食谱' } }).length, 5)
})
test('undefined completion denominator is not presented as zero completion', () => {
  assert.equal(formatPercent(null), '暂无可统计事项')
  assert.equal(formatPercent(0), '0%')
  assert.equal(formatPercent(66.6666), '66.7%')
})
test('grouped days and meals are chronological without mutating persisted historical items', () => {
  const items = [{ date: '2026-11-02', meal_type: 'dinner', feedback: { status: 'completed' } }, { date: '2026-11-01', meal_type: 'lunch' }, { date: '2026-11-02', meal_type: 'breakfast' }]
  const before = structuredClone(items), grouped = groupPlanDays(items)
  assert.deepEqual(grouped.map(day => day.date), ['2026-11-01', '2026-11-02'])
  assert.deepEqual(grouped[1].items.map(item => item.meal_type), ['breakfast', 'dinner'])
  assert.deepEqual(items, before)
})
test('weekly input preserves explicit goals and context, with no invented meal allocation', () => {
  const form = { start_date: '2026-11-01', portions: 1, selected_goal_ids: [2, 8], ratios: { breakfast: '', lunch: null, dinner: 35 } }
  const input = buildWeeklyInput(form, 'profile-rules-goals-version')
  assert.deepEqual(input.meal_ratios, { breakfast: null, lunch: null, dinner: 0.35 })
  assert.deepEqual(input.selected_goal_ids, [2, 8])
  assert.equal(input.expected_context_hash, 'profile-rules-goals-version')
  input.selected_goal_ids.push(99)
  assert.deepEqual(form.selected_goal_ids, [2, 8])
  assert.equal('calories_kcal' in input, false)
})
test('slow older context responses cannot replace a newer generation or disposed view', async () => {
  const gate = createLatestRequest(), old = gate.begin()
  const newer = gate.begin()
  await Promise.resolve()
  assert.equal(gate.current(old), false)
  assert.equal(gate.current(newer), true)
  gate.invalidate()
  assert.equal(gate.current(newer), false)
})
test('condition edit invalidates pending responses before replacement request begins', () => {
  const gate = createLatestRequest(), request = gate.begin()
  gate.invalidate()
  assert.equal(gate.current(request), false)
  assert.equal(gate.current(gate.begin()), true)
})
test('backend blocking reasons stay visible instead of being interpreted as recommendations', () => {
  assert.equal(messageText('过敏信息待确认'), '过敏信息待确认')
  assert.equal(messageText({ code: 'PROFILE_CHANGED', message: '请重新核对' }), '请重新核对')
  assert.equal(messageText({ reason: '成分未知' }), '成分未知')
})

function lifecycleHarness() {
  let time = 1000, last = 1000, busy = false, visible = true, reads = 0, nextId = 0
  const timers = new Map()
  const gate = createLifecycleRefresh({ getLastRefresh: () => last, isBusy: () => busy, isVisible: () => visible, now: () => time,
    refresh: () => { reads++; last = time }, schedule: (callback, delay) => { const id = ++nextId; timers.set(id, { callback, due: time + delay }); return id }, cancel: id => timers.delete(id) })
  return { gate, reads: () => reads, busy: value => { busy = value }, visible: value => { visible = value },
    advance(delta) { time += delta; for (const [id, task] of [...timers]) if (task.due <= time) { timers.delete(id); task.callback() } } }
}
test('focus within throttle window queues a trailing profile read rather than losing the event', () => {
  const h = lifecycleHarness()
  h.advance(100); h.gate.request(); h.gate.request()
  assert.equal(h.reads(), 0)
  h.advance(1399); assert.equal(h.reads(), 0)
  h.advance(1); assert.equal(h.reads(), 1)
  h.advance(5000); assert.equal(h.reads(), 1)
})
test('focus during a mutation survives until the action settles and resumes', () => {
  const h = lifecycleHarness()
  h.busy(true); h.gate.request(); h.advance(2000)
  assert.equal(h.reads(), 0)
  h.busy(false); h.gate.resume()
  assert.equal(h.reads(), 1)
})
test('hidden or disposed weekly workspace does not run pending private-data refreshes', () => {
  const h = lifecycleHarness()
  h.gate.request(); h.visible(false); h.advance(1500)
  assert.equal(h.reads(), 0)
  h.visible(true); h.gate.request(); assert.equal(h.reads(), 1)
  h.gate.request(); h.gate.dispose(); h.advance(1500); h.gate.resume()
  assert.equal(h.reads(), 1)
})
