<script setup>
import { onMounted, onUnmounted } from 'vue'
import { dueEvents } from './schedule'
import { checkSnooze, clearReminderAccess, dismissReminder, refreshReminders, reminderAlert, reminderSettings, remindersEnabled, snoozeIsDue, stopRinging, triggerReminder } from './reminders'
let timer, last = Date.now(), lastAccessCheck = 0, checking = false
const seen = new Set()
async function tick() {
  if (checking) return
  const now = Date.now()
  if (remindersEnabled.value) {
    // Verify live permission before emitting a notification or a snoozed alarm.
    if (now - lastAccessCheck >= 30000 || dueEvents(reminderSettings.value, last, now).length || snoozeIsDue(now)) {
      checking = true
      const allowed = await refreshReminders()
      checking = false; lastAccessCheck = now
      if (!allowed || !remindersEnabled.value) { last = now; return }
    }
    for (const event of dueEvents(reminderSettings.value, last, now)) {
      if (seen.has(event.id)) continue
      seen.add(event.id)
      let stored = false
      try { stored = localStorage.getItem('sleep-last-event') === event.id; localStorage.setItem('sleep-last-event', event.id) } catch { /* In-memory deduplication remains available. */ }
      if (!stored) triggerReminder(event)
    }
    checkSnooze(now)
  }
  last = now
}
function sessionChanged() { clearReminderAccess(); seen.clear(); last = Date.now(); lastAccessCheck = 0; refreshReminders() }
onMounted(() => {
  refreshReminders(); timer = setInterval(tick, 1000)
  window.addEventListener('health-auth-changed', sessionChanged)
  window.addEventListener('health-permissions-changed', sessionChanged)
  window.addEventListener('sleep-access-denied', clearReminderAccess)
  window.addEventListener('focus', refreshReminders)
})
onUnmounted(() => {
  clearInterval(timer); stopRinging()
  window.removeEventListener('health-auth-changed', sessionChanged)
  window.removeEventListener('health-permissions-changed', sessionChanged)
  window.removeEventListener('sleep-access-denied', clearReminderAccess)
  window.removeEventListener('focus', refreshReminders)
})
</script>
<template><aside v-if="reminderAlert" class="sleep-reminder-banner" role="alert"><div><strong>{{ reminderAlert.title }}</strong><p>{{ reminderAlert.message }}</p></div><button v-if="reminderAlert.kind === 'alarm'" class="button secondary" @click="dismissReminder(true)">5 分钟后提醒</button><button class="button primary" @click="dismissReminder()">知道了</button></aside></template>
