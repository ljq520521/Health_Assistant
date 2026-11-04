<script setup>
import { computed, reactive, ref } from 'vue'
import { displayTime, hours, json, request, shanghaiInput, today } from '../../api/sleep'
import SleepDialog from './SleepDialog.vue'

const props = defineProps({ records: Array, profile: Object, canEdit: Boolean })
const emit = defineEmits(['changed'])
const editor = ref(false), editingId = ref(null), deleting = ref(null), selected = ref(null)
const busy = ref(false), error = ref(''), query = ref('')
const form = reactive({})
const filtered = computed(() => (props.records || []).filter(row => !query.value || row.wake_date === query.value))
function open(row) {
  editingId.value = row?.id ?? null
  const day = today()
  const yesterday = shanghaiInput(new Date(`${day}T00:00:00+08:00`).getTime() - 86400000).slice(0, 10)
  Object.assign(form, row ? {
    sleep_at: shanghaiInput(row.sleep_at), wake_at: shanghaiInput(row.wake_at),
    deep_minutes: row.deep_minutes ?? '', light_minutes: row.light_minutes ?? '',
    awakenings: row.awakenings, quality: row.quality ?? '', notes: row.notes,
  } : { sleep_at: `${yesterday}T23:00`, wake_at: `${day}T07:00`, deep_minutes: '', light_minutes: '', awakenings: 0, quality: '', notes: '' })
  error.value = ''; editor.value = true
}
async function save() {
  busy.value = true; error.value = ''
  try {
    const payload = { ...form, sleep_at: `${form.sleep_at}:00+08:00`, wake_at: `${form.wake_at}:00+08:00` }
    for (const key of ['deep_minutes', 'light_minutes', 'quality']) payload[key] = form[key] === '' ? null : Number(form[key])
    payload.awakenings = Number(form.awakenings)
    await request(`/sleep-records${editingId.value ? `/${editingId.value}` : ''}`, json(editingId.value ? 'PUT' : 'POST', payload))
    editor.value = false; emit('changed')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function remove() {
  busy.value = true; error.value = ''
  try { await request(`/sleep-records/${deleting.value.id}`, { method: 'DELETE' }); deleting.value = null; emit('changed') }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <section class="sleep-panel">
    <div class="sleep-section-title"><div><h2>睡眠记录</h2><p>按醒来日期归档 · {{ records.length }} 条记录</p></div><div class="sleep-actions"><label class="sr-only" for="record-date">筛选醒来日期</label><input id="record-date" v-model="query" type="date" /><button v-if="query" class="sleep-text-button" @click="query = ''">清除</button><button class="button primary" :disabled="!profile || !canEdit" @click="open()">＋ 记录睡眠</button></div></div>
    <div v-if="!filtered.length" class="sleep-empty"><h3>还没有这段时间的记录</h3><p>记下昨晚的入睡与醒来时间，让每一次休息都有迹可循。</p></div>
    <div v-else class="sleep-table-wrap"><table class="sleep-table"><thead><tr><th>醒来日期</th><th>入睡 → 醒来（上海）</th><th>时长</th><th>深 / 浅睡</th><th>作息分</th><th>操作</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id"><td><strong>{{ row.wake_date }}</strong><small v-if="row.alerts.length" class="sleep-warning">{{ row.alerts.length }} 项偏离提示</small></td><td>{{ displayTime(row.sleep_at) }}<br />→ {{ displayTime(row.wake_at) }}</td><td>{{ hours(row.duration_minutes) }}</td><td>{{ row.deep_minutes ?? '—' }} / {{ row.light_minutes ?? '—' }} 分钟</td><td><button class="sleep-score-link" @click="selected = row">{{ row.score }} 分 ↗</button></td><td><div class="sleep-actions"><button :disabled="!canEdit" class="sleep-text-button" :aria-label="`编辑 ${row.wake_date} 的记录`" @click="open(row)">编辑</button><button :disabled="!canEdit" class="sleep-text-button danger" :aria-label="`删除 ${row.wake_date} 的记录`" @click="deleting = row; error = ''">删除</button></div></td></tr></tbody></table></div>
  </section>
  <SleepDialog v-if="editor" :title="editingId ? '编辑睡眠记录' : '记录一次睡眠'" :busy="busy" @close="editor = false">
    <form class="sleep-form" @submit.prevent="save"><p class="sleep-muted">所有时间按北京时间（Asia/Shanghai）填写，可记录跨夜睡眠。</p><div class="sleep-form-grid">
      <label>入睡时间<input v-model="form.sleep_at" type="datetime-local" required /></label><label>醒来时间<input v-model="form.wake_at" type="datetime-local" required /></label>
      <label>深睡（分钟，可选）<input v-model="form.deep_minutes" type="number" min="0" max="1440" step="1" placeholder="不知道可留空" /></label><label>浅睡（分钟，可选）<input v-model="form.light_minutes" type="number" min="0" max="1440" step="1" placeholder="不知道可留空" /></label>
      <label>夜醒次数<input v-model="form.awakenings" type="number" min="0" max="50" step="1" required /></label><label>醒来后的感受<select v-model="form.quality"><option value="">暂不评分</option><option v-for="(label, index) in ['很差', '较差', '一般', '较好', '很好']" :key="label" :value="index + 1">{{ index + 1 }} 分 · {{ label }}</option></select></label>
    </div><label>备注<textarea v-model="form.notes" rows="3" maxlength="2000" placeholder="例如：睡前阅读，夜里醒来一次" /></label><p class="sleep-muted">深浅睡为手动记录，未填写部分保留为未知，不会自动推断。</p><p v-if="error" class="sleep-error" role="alert">{{ error }}</p><div class="sleep-form-footer"><button type="button" class="button secondary" :disabled="busy" @click="editor = false">取消</button><button class="button primary" :disabled="busy">{{ busy ? '保存中…' : '保存记录' }}</button></div></form>
  </SleepDialog>
  <SleepDialog v-if="deleting" title="删除这条睡眠记录？" :busy="busy" @close="deleting = null"><p>{{ deleting.wake_date }} · {{ hours(deleting.duration_minutes) }}。删除后统计和报告也会更新。</p><p v-if="error" class="sleep-error" role="alert">{{ error }}</p><div class="sleep-form-footer"><button class="button secondary" :disabled="busy" @click="deleting = null">保留记录</button><button class="button sleep-danger" :disabled="busy" @click="remove">确认删除</button></div></SleepDialog>
  <SleepDialog v-if="selected" title="睡眠质量评估" @close="selected = null"><div class="sleep-score-hero">{{ selected.score }}<small>/ 100</small></div><p class="sleep-muted">按当前目标计算的作息参考分，不是医学量表。</p><div v-for="dimension in selected.dimensions" :key="dimension.name" class="sleep-dimension"><div><span>{{ dimension.name }}</span><strong>{{ dimension.points }} / {{ dimension.max }}</strong></div><progress :value="dimension.points" :max="dimension.max" /></div><p v-if="!selected.assessment_complete" class="sleep-muted">未填主观评分，其余维度按比例换算为百分制。</p><p>夜醒 {{ selected.awakenings }} 次 · 未记录睡眠阶段 {{ selected.stage_unrecorded_minutes }} 分钟</p><ul v-if="selected.alerts.length" class="sleep-alerts"><li v-for="alert in selected.alerts" :key="alert">{{ alert }}</li></ul><p v-if="selected.notes" class="sleep-note">{{ selected.notes }}</p></SleepDialog>
</template>
