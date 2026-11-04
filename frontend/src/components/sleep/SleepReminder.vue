<script setup>
import { onMounted, onUnmounted } from 'vue'
import { dueEvents } from './schedule'
import { checkSnooze, dismissReminder, refreshReminders, reminderAlert, reminderSettings, remindersEnabled, stopRinging, triggerReminder } from './reminders'
let timer, last = Date.now()
const seen = new Set()
function tick() {
  const now = Date.now()
  if (remindersEnabled.value) {
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
onMounted(() => { refreshReminders().catch(() => {}); timer = setInterval(tick, 1000) })
onUnmounted(() => { clearInterval(timer); stopRinging() })
</script>
<template><aside v-if="reminderAlert" class="sleep-reminder-banner" role="alert"><div><strong>{{ reminderAlert.title }}</strong><p>{{ reminderAlert.message }}</p></div><button v-if="reminderAlert.kind === 'alarm'" class="button secondary" @click="dismissReminder(true)">5 分钟后提醒</button><button class="button primary" @click="dismissReminder()">知道了</button></aside></template>
