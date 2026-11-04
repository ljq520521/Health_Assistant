<script setup>
import { computed, onMounted, ref } from 'vue'
import { hours, json, request, today } from '../api/sleep'
import SleepRecords from '../components/sleep/SleepRecords.vue'
import SleepTrend from '../components/sleep/SleepTrend.vue'
import SleepAudio from '../components/sleep/SleepAudio.vue'
import SleepSettings from '../components/sleep/SleepSettings.vue'
import SleepReport from '../components/sleep/SleepReport.vue'
import { reminderSettings } from '../components/sleep/reminders'
import '../components/sleep/sleep.css'

const tab = ref('overview'), period = ref('week'), endDate = ref(today())
const analysis = ref(null), records = ref([]), profile = ref(null), settings = ref(null)
const loading = ref(false), error = ref(''), name = ref(''), creating = ref(false)
let requestVersion = 0
const summary = computed(() => analysis.value?.summary || {})
async function load() {
  const version = ++requestVersion; loading.value = true; error.value = ''
  try {
    if (!endDate.value) throw new Error('请选择截止日期')
    const [report, rows, config, account] = await Promise.all([
      request(`/sleep/analysis?${new URLSearchParams({ period: period.value, end_date: endDate.value })}`),
      request('/sleep-records'), request('/sleep/settings'), request('/sleep/profile'),
    ])
    if (version !== requestVersion) return
    analysis.value = report; records.value = rows.items; settings.value = config
    profile.value = account.profile; reminderSettings.value = config
  } catch (e) { if (version === requestVersion) error.value = e.message }
  finally { if (version === requestVersion) loading.value = false }
}
async function createProfile() {
  creating.value = true; error.value = ''
  try { await request('/sleep/profile', json('POST', { display_name: name.value })); await load() }
  catch (e) { error.value = e.message } finally { creating.value = false }
}
onMounted(load)
</script>
<template>
  <div class="sleep-page">
    <div class="sleep-heading"><div><p class="eyebrow">SLEEP & REST</p><h1>好好睡觉，也是一件正经事。</h1><p>记录每一晚，找到属于自己的休息节奏。</p></div><span class="sleep-chip">睡眠监测 · 成员 D</span></div>
    <section class="sleep-hero"><div><span class="sleep-hero-tag">YOUR NIGHT, YOUR RHYTHM</span><h2>把一天的忙碌，<br />留在晚安之前。</h2><p>睡眠记录、趋势、助眠声音与作息提醒，<br />一起照顾你的夜晚。</p></div><div class="sleep-moon" aria-hidden="true"><span>☾</span><i>✦</i><i>·</i></div><div class="sleep-hero-plan"><small>计划入睡</small><strong>{{ settings?.bedtime || '23:00' }}</strong><button @click="tab = 'settings'">调整我的作息 →</button></div></section>
    <div v-if="error" class="sleep-error sleep-load-error" role="alert">{{ error }}<button class="button secondary" :disabled="loading" @click="load">重新加载</button></div>
    <p v-if="loading" class="sleep-muted" role="status">正在更新睡眠数据…</p>
    <form v-if="analysis && !profile" class="sleep-onboarding" @submit.prevent="createProfile"><div><h2>先建立你的本地档案</h2><p>只需一个称呼，睡眠记录就能保存到本机。</p></div><label><span class="sr-only">档案称呼</span><input v-model="name" required maxlength="50" placeholder="怎么称呼你？" /></label><button class="button primary" :disabled="creating">{{ creating ? '创建中…' : '建立档案' }}</button></form>
    <template v-if="analysis"><div class="sleep-toolbar"><div class="sleep-tabs" aria-label="睡眠功能"><button v-for="item in [['overview','记录与分析'],['audio','助眠音频'],['settings','作息与闹钟'],['report','睡眠报告']]" :key="item[0]" :aria-pressed="tab === item[0]" :class="{ active: tab === item[0] }" @click="tab = item[0]">{{ item[1] }}</button></div><div v-if="tab === 'overview' || tab === 'report'" class="sleep-actions"><div class="sleep-segment"><button :class="{ active: period === 'week' }" @click="period = 'week'; load()">近 7 天</button><button :class="{ active: period === 'month' }" @click="period = 'month'; load()">近 30 天</button></div><label class="sleep-end-date">截止<input v-model="endDate" aria-label="统计截止日期" type="date" :max="today()" @change="load" /></label></div></div>
      <template v-if="tab === 'overview'"><div class="sleep-metrics"><article><span>平均睡眠时长</span><strong>{{ hours(summary.average_minutes) }}</strong><small v-if="summary.change_minutes != null">较前期 {{ summary.change_minutes >= 0 ? '+' : '' }}{{ summary.change_minutes }} 分钟</small><small v-else>记录后自动计算</small></article><article><span>平均作息分</span><strong>{{ summary.average_score ?? '—' }}<small> / 100</small></strong><small>时长 · 连续性 · 规律 · 感受</small></article><article><span>记录覆盖</span><strong>{{ summary.recorded_days }}<small> / {{ summary.period_days }} 天</small></strong><small>未记录日期不计入均值</small></article><article><span>达到时长目标</span><strong>{{ summary.target_days }}<small> 天</small></strong><small>当前目标 {{ hours(settings.target_minutes) }}</small></article></div><SleepTrend :analysis="analysis" /><SleepRecords :records="records" :profile="profile" @changed="load" /><p class="sleep-muted sleep-bottom-note">{{ analysis.notice }}</p></template>
      <SleepAudio v-if="tab === 'audio'" /><SleepSettings v-if="tab === 'settings'" :settings="settings" :profile="profile" @changed="load" /><SleepReport v-if="tab === 'report'" :analysis="analysis" :profile="profile" />
    </template>
  </div>
</template>
