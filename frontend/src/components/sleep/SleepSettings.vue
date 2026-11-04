<script setup>
import { reactive, ref, watch } from 'vue'
import { json, request } from '../../api/sleep'
import { disableReminders, enableReminders, refreshReminders, remindersEnabled, reminderStatus, triggerReminder } from './reminders'
const props = defineProps({ settings: Object, profile: Object, canEdit: Boolean })
const emit = defineEmits(['changed'])
const form = reactive({}), targetHours = ref(8), busy = ref(false), error = ref(''), saved = ref(false)
const keys = ['bedtime', 'alarm_time', 'reminder_minutes', 'bedtime_enabled', 'alarm_enabled', 'smart_alarm', 'weekdays']
watch(() => props.settings, value => { if (value) { for (const key of keys) form[key] = Array.isArray(value[key]) ? [...value[key]] : value[key]; targetHours.value = value.target_minutes / 60 } }, { immediate: true })
async function save() {
  busy.value = true; error.value = ''; saved.value = false
  try {
    if (!form.weekdays.length) throw new Error('请至少选择一天')
    await request('/sleep/settings', json('PUT', { ...form, target_minutes: Math.round(Number(targetHours.value) * 60), reminder_minutes: Number(form.reminder_minutes) }))
    await refreshReminders(); saved.value = true; emit('changed')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function testAlarm() { if (await enableReminders()) triggerReminder({ kind: 'alarm', title: '闹钟试听', message: '这是一次测试提醒，点击“知道了”停止。' }) }
</script>
<template>
  <div class="sleep-settings-layout"><section class="sleep-panel"><div class="sleep-section-title"><div><h2>把休息留在日程里</h2><p>设置个人目标与重复提醒 · 时区 Asia/Shanghai</p></div></div><form class="sleep-form" @submit.prevent="save"><fieldset class="sleep-form sleep-settings-fields" :disabled="!canEdit || busy"><div class="sleep-form-grid">
    <label>目标睡眠（小时）<input v-model="targetHours" type="number" min="3" max="12" step="0.25" required /></label><label>计划入睡时间<input v-model="form.bedtime" type="time" required /></label>
    <label>最晚起床时间<input v-model="form.alarm_time" type="time" required /></label><label>提前几分钟提醒入睡<input v-model="form.reminder_minutes" type="number" min="0" max="120" step="1" required /></label>
  </div><fieldset class="sleep-weekdays"><legend>重复日期</legend><label v-for="(day, index) in ['一','二','三','四','五','六','日']" :key="day"><input v-model="form.weekdays" type="checkbox" :value="index" /><span>周{{ day }}</span></label></fieldset>
    <label class="sleep-toggle"><input v-model="form.bedtime_enabled" type="checkbox" /><span>睡前提醒<small>在计划入睡前弹出提示</small></span></label>
    <label class="sleep-toggle"><input v-model="form.alarm_enabled" type="checkbox" /><span>起床闹钟<small>声音、页面提示与 5 分钟稍后提醒</small></span></label>
    <label class="sleep-toggle"><input v-model="form.smart_alarm" type="checkbox" /><span>智能闹钟（时间估算）<small>以计划入睡时间为起点，按 90 分钟间隔，尝试在最晚起床前 30 分钟内选择时间；没有候选则准点响铃。</small></span></label>
    <p class="sleep-muted">这是作息时间估算，不能识别实时浅睡阶段，也不保证在某一睡眠阶段唤醒。重复日期分别指计划入睡日和计划起床日。</p>
    <p v-if="error" role="alert" class="sleep-error">{{ error }}</p><p v-if="saved" class="sleep-success" role="status">设置已保存</p><div class="sleep-form-footer"><button class="button primary" :disabled="busy || !profile || !canEdit">{{ busy ? '保存中…' : '保存作息设置' }}</button></div>
  </fieldset></form></section><aside class="sleep-panel sleep-settings-note"><p class="eyebrow">YOUR EVENING ROUTINE</p><h2>今晚，给自己一个约定。</h2><div class="sleep-routine-time"><span>睡前提醒</span><strong>{{ settings.reminder_time }}</strong><small>{{ settings.bedtime_enabled ? '已设置' : '未开启' }}</small></div><div class="sleep-routine-time"><span>实际闹钟时间</span><strong>{{ settings.effective_alarm_time }}</strong><small>{{ settings.alarm_enabled ? '已设置' : '未开启' }}</small></div><p>网页提醒需要页面保持打开、设备保持唤醒。关闭页面或设备休眠后无法保证响铃。</p><p>保存规则后，还需点击下方按钮为本次页面开启声音；刷新页面需重新开启。</p><button class="button primary" @click="remindersEnabled ? disableReminders() : enableReminders()">{{ remindersEnabled ? '停止本次页面提醒' : '开启本次提醒与声音' }}</button><button class="button secondary" @click="testAlarm">试听闹钟</button><p class="sleep-muted" role="status">{{ reminderStatus }}</p></aside></div>
</template>
