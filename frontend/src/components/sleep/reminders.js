import { ref } from 'vue'
import { request } from '../../api/sleep.js'
import { getToken } from '../../api/profile.js'
export const reminderSettings = ref(null)
export const remindersEnabled = ref(false)
export const reminderStatus = ref('本次页面尚未启用提醒')
export const reminderAlert = ref(null)
let context, ringing, timeout, snoozeAt = 0, accessVersion = 0

export function clearReminderAccess() {
  accessVersion++
  disableReminders(); reminderSettings.value = null
  context?.suspend().catch(() => {})
  reminderStatus.value = '登录或授权已改变，请确认权限后重新启用提醒'
}
export async function refreshReminders() {
  const token = getToken(), version = ++accessVersion
  if (!token) { clearReminderAccess(); return false }
  try {
    const settings = await request('/sleep/settings')
    if (token !== getToken() || version !== accessVersion) return false
    reminderSettings.value = settings
    return true
  } catch {
    if (version === accessVersion) clearReminderAccess()
    return false
  }
}
export async function enableReminders() {
  const token = getToken()
  let soundReady = false
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext
    context ||= new AudioContext()
    await context.resume()
    soundReady = true
  } catch { /* Authorized users can still use in-page reminders. */ }
  if (!await refreshReminders() || token !== getToken()) return false
  remindersEnabled.value = true
  reminderStatus.value = soundReady ? '本次页面提醒已启用，请保持页面打开和设备唤醒' : '已启用页面提示；声音不可用，请检查浏览器权限'
  if ('Notification' in window && Notification.permission === 'default') {
    try { await Notification.requestPermission() } catch { /* Banner remains available. */ }
  }
  return remindersEnabled.value && token === getToken()
}
function beep() {
  if (!context || context.state !== 'running') return
  const tone = context.createOscillator(), gain = context.createGain()
  tone.frequency.value = 660; gain.gain.value = 0
  tone.connect(gain); gain.connect(context.destination)
  gain.gain.setTargetAtTime(0.12, context.currentTime, 0.1)
  gain.gain.setTargetAtTime(0, context.currentTime + 0.5, 0.1)
  tone.start(); tone.stop(context.currentTime + 1)
  tone.onended = () => { tone.disconnect(); gain.disconnect() }
}
export function stopRinging() { clearInterval(ringing); clearTimeout(timeout) }
export function triggerReminder(event) {
  if (!remindersEnabled.value || !getToken()) return
  stopRinging(); reminderAlert.value = event; beep()
  if (event.kind === 'alarm') { ringing = setInterval(beep, 2000); timeout = setTimeout(stopRinging, 60000) }
  if ('Notification' in window && Notification.permission === 'granted') {
    try { new Notification(event.title, { body: event.message, tag: 'sleep-reminder' }) } catch { /* Page banner is the fallback. */ }
  }
}
export function dismissReminder(snooze = false) {
  stopRinging(); reminderAlert.value = null
  snoozeAt = snooze ? Date.now() + 5 * 60000 : 0
}
export function checkSnooze(now) {
  if (snoozeAt && now >= snoozeAt) { const elapsed = now - snoozeAt; snoozeAt = 0; if (elapsed <= 90000) triggerReminder({ kind: 'alarm', title: '再次提醒：到起床时间了', message: '稍后提醒的 5 分钟已到。' }) }
}
export function snoozeIsDue(now) { return Boolean(snoozeAt && now >= snoozeAt) }
export function disableReminders() { remindersEnabled.value = false; dismissReminder(); reminderStatus.value = '本次页面提醒已停止' }
