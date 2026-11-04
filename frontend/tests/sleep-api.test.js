import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'

const storage = new Map()
globalThis.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: key => storage.delete(key),
}
globalThis.window = new EventTarget()
const profile = await import('../src/api/profile.js')
const sleep = await import('../src/api/sleep.js')
const reminders = await import('../src/components/sleep/reminders.js')
let calls, events
for (const type of ['health-auth-changed', 'health-permissions-changed', 'sleep-access-denied']) {
  window.addEventListener(type, event => events?.push({ type, detail: event.detail }))
}
const ok = body => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
const denied = status => new Response(JSON.stringify({ detail: 'Access denied' }), { status })
beforeEach(() => {
  profile.setToken('current-account')
  calls = []; events = []
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return ok({ items: [] }) }
})
afterEach(() => {
  reminders.clearReminderAccess()
  profile.logout()
})

test('anonymous sleep requests do not contact the backend', async () => {
  profile.logout()
  await assert.rejects(sleep.request('/sleep-records'), { status: 401 })
  assert.equal(calls.length, 0)
})

test('JSON and raw audio writes use the shared token only in the authorization header', async () => {
  await sleep.request('/sleep-records', sleep.json('POST', { notes: 'private' }))
  const wav = new Blob(['audio bytes'], { type: 'audio/wav' })
  await sleep.request('/sleep/content/upload?title=Test', {
    method: 'POST', body: wav, headers: { 'Content-Type': 'audio/wav' },
  })
  for (const { url, options } of calls) {
    assert.equal(options.headers.Authorization, 'Bearer current-account')
    assert.equal(options.cache, 'no-store')
    assert.ok(!url.includes('current-account'))
  }
  assert.equal(calls[0].options.headers['Content-Type'], 'application/json')
  assert.equal(calls[1].options.body, wav)
  assert.equal(calls[1].options.headers['Content-Type'], 'audio/wav')
})

test('uploaded audio is fetched with authentication and returned as a blob', async () => {
  fetch = async (url, options) => {
    calls.push({ url, options })
    return new Response('wave bytes', { headers: { 'Content-Type': 'audio/wav' } })
  }
  const result = await sleep.request('/sleep/content/7/audio', { responseType: 'blob' })
  assert.equal(await result.text(), 'wave bytes')
  assert.equal(calls[0].options.headers.Authorization, 'Bearer current-account')
  assert.equal(calls[0].options.responseType, undefined)
})

test('CSV download uses an authenticated fetch and a blob URL without exposing the token', async () => {
  fetch = async (url, options) => { calls.push({ url, options }); return new Response('date,minutes\n2026-09-21,480') }
  let clicked = false
  const anchor = { click: () => { clicked = true } }
  globalThis.document = { createElement: tag => { assert.equal(tag, 'a'); return anchor } }
  await sleep.downloadReport('week', '2026-09-21')
  assert.ok(clicked)
  assert.ok(anchor.href.startsWith('blob:'))
  assert.equal(calls[0].options.headers.Authorization, 'Bearer current-account')
  assert.ok(calls[0].url.includes('format=csv'))
  assert.ok(!calls[0].url.includes('current-account'))
  URL.revokeObjectURL(anchor.href)
  delete globalThis.document
})

test('401 invalidates the shared session and notifies mounted sleep components', async () => {
  fetch = async () => denied(401)
  await assert.rejects(sleep.request('/sleep-records'), { status: 401 })
  assert.equal(profile.getToken(), '')
  assert.ok(events.some(event => event.type === 'health-auth-changed'))
  assert.ok(events.some(event => event.type === 'sleep-access-denied' && event.detail.status === 401))
})

test('403 clears private views without discarding the account needed to restore consent', async () => {
  fetch = async () => denied(403)
  await assert.rejects(sleep.request('/sleep/report', { responseType: 'blob' }), { status: 403 })
  assert.equal(profile.getToken(), 'current-account')
  assert.ok(events.some(event => event.type === 'sleep-access-denied' && event.detail.status === 403))
})

test('a response from a previous account cannot populate the next account view', async () => {
  let resolve
  fetch = () => new Promise(done => { resolve = done })
  const pending = sleep.request('/sleep-records')
  profile.setToken('next-account')
  events = []
  resolve(ok({ items: [{ notes: 'old private record' }] }))
  await assert.rejects(pending, { status: 401 })
  assert.equal(profile.getToken(), 'next-account')
  assert.deepEqual(events, [])
})

test('logout while a binary response is downloading discards the blob', async () => {
  let resolveBody, started
  const bodyStarted = new Promise(done => { started = done })
  fetch = async () => ({ ok: true, status: 200, blob: () => {
    started()
    return new Promise(done => { resolveBody = done })
  } })
  const pending = sleep.request('/sleep/content/7/audio', { responseType: 'blob' })
  await bodyStarted
  profile.logout()
  resolveBody(new Blob(['private audio']))
  await assert.rejects(pending, { status: 401 })
})

test('a late profile 401 does not log out a newly logged in account', async () => {
  let resolve
  fetch = () => new Promise(done => { resolve = done })
  const pending = profile.getMe()
  profile.setToken('next-account')
  resolve(denied(401))
  await assert.rejects(pending, { status: 401 })
  assert.equal(profile.getToken(), 'next-account')
})

test('privacy updates and cross-tab logout notify listeners', async () => {
  await profile.updatePrivacy({ consent_health_data: false, mask_sensitive: false, analytics_consent: false })
  assert.ok(events.some(event => event.type === 'health-permissions-changed'))
  const changed = new Event('storage')
  Object.assign(changed, { key: 'health_profile_token', newValue: null })
  window.dispatchEvent(changed)
  assert.equal(profile.getToken(), '')
  assert.ok(events.some(event => event.type === 'health-auth-changed'))
})

test('ordinary validation errors do not invalidate the login', async () => {
  fetch = async () => new Response(JSON.stringify({ detail: [{ msg: 'Invalid date' }] }), { status: 422 })
  await assert.rejects(sleep.request('/sleep-records', sleep.json('POST', {})), { status: 422, message: 'Invalid date' })
  assert.equal(profile.getToken(), 'current-account')
  assert.deepEqual(events, [])
})

test('reminders require successful authorization before enabling', async () => {
  fetch = async () => denied(403)
  assert.equal(await reminders.enableReminders(), false)
  reminders.triggerReminder({ kind: 'bedtime', title: 'Must stay hidden' })
  assert.equal(reminders.remindersEnabled.value, false)
  assert.equal(reminders.reminderAlert.value, null)
})

test('revoked permissions clear active and snoozed reminders and private settings', async () => {
  fetch = async () => ok({ bedtime: '23:00', alarm_time: '07:00' })
  assert.equal(await reminders.enableReminders(), true)
  reminders.triggerReminder({ kind: 'bedtime', title: 'Bedtime' })
  assert.equal(reminders.reminderAlert.value.title, 'Bedtime')
  reminders.dismissReminder(true)
  fetch = async () => denied(403)
  assert.equal(await reminders.refreshReminders(), false)
  reminders.checkSnooze(Date.now() + 5 * 60000 + 1000)
  assert.equal(reminders.remindersEnabled.value, false)
  assert.equal(reminders.reminderSettings.value, null)
  assert.equal(reminders.reminderAlert.value, null)
})

test('a pending reminder refresh cannot restore settings after access was cleared', async () => {
  let resolve
  fetch = () => new Promise(done => { resolve = done })
  const pending = reminders.refreshReminders()
  reminders.clearReminderAccess()
  resolve(ok({ bedtime: 'private' }))
  assert.equal(await pending, false)
  assert.equal(reminders.reminderSettings.value, null)
})
