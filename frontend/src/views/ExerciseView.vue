<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import ExerciseFormDialog from '../components/exercise/ExerciseFormDialog.vue'
import ExerciseRecommendation from '../components/exercise/ExerciseRecommendation.vue'
import ExerciseTrendChart from '../components/exercise/ExerciseTrendChart.vue'
import { deleteExercise, listExercise } from '../api/exercise.js'
import {
  INTENSITY_LABELS,
  buildTrend,
  formatMinutes,
  groupByDate,
  shiftDate,
  summarize,
  todayInZone,
  validDate,
  weekdayLabel,
} from '../components/exercise/exerciseStats.js'
import { modules } from '../data/modules'

const module = modules.find((item) => item.code === 'exercise')
const timeZone = 'Asia/Shanghai'
const today = todayInZone(timeZone)

const records = ref([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const noProfile = ref(false)
const filters = reactive({ date_from: '', date_to: '' })

const editor = ref(null)
const recommendation = ref(null)
const confirmation = ref(null)
const deleting = ref(null)
const deleteError = ref('')
let returnFocus = null
let loadVersion = 0

const summary = computed(() => summarize(records.value))
const groups = computed(() => groupByDate(records.value))
const trendEnd = computed(() => (validDate(filters.date_to) ? filters.date_to : today))
const trend = computed(() => buildTrend(records.value, { days: 14, endDate: trendEnd.value }))
const trendRange = computed(() => `${shiftDate(trendEnd.value, -13)} ~ ${trendEnd.value}`)
const highRatio = computed(() =>
  summary.value.totalMinutes
    ? Math.round((summary.value.intensityMinutes.high / summary.value.totalMinutes) * 100)
    : 0,
)
const filterActive = computed(() => Boolean(filters.date_from || filters.date_to))

function handleError(err, target = error) {
  target.value = err.message
  if (err.status === 409) {
    noProfile.value = true
    records.value = []
  }
}

async function load() {
  error.value = ''
  if (filters.date_from && !validDate(filters.date_from)) {
    error.value = '请输入合法的开始日期'
    return
  }
  if (filters.date_to && !validDate(filters.date_to)) {
    error.value = '请输入合法的结束日期'
    return
  }
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
    error.value = '开始日期不能晚于结束日期'
    return
  }
  const version = ++loadVersion
  loading.value = true
  try {
    const data = await listExercise({ ...filters })
    if (version !== loadVersion) return
    records.value = data.items
    noProfile.value = false
  } catch (err) {
    if (version === loadVersion) handleError(err)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function applyPreset(days) {
  filters.date_to = days ? today : ''
  filters.date_from = days ? shiftDate(today, -(days - 1)) : ''
  load()
}

function clearFilters() {
  filters.date_from = ''
  filters.date_to = ''
  load()
}

function openEditor(record = null) {
  editor.value.open(record)
}

function onSaved(message) {
  success.value = message
  load()
  recommendation.value?.reload()
}

function askDelete(record) {
  returnFocus = document.activeElement
  deleting.value = record
  deleteError.value = ''
  confirmation.value.showModal()
}

function closeConfirm() {
  if (busy.value) return
  confirmation.value.close()
  returnFocus?.focus()
}

async function remove() {
  busy.value = true
  deleteError.value = ''
  success.value = ''
  try {
    await deleteExercise(deleting.value.id)
    confirmation.value.close()
    success.value = '运动记录已删除'
    returnFocus?.focus()
    await load()
    recommendation.value?.reload()
  } catch (err) {
    deleteError.value = err.message
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="module-overview blue">
    <RouterLink class="back-link" to="/">← 返回总览</RouterLink>

    <div class="page-heading exercise-heading">
      <div>
        <p class="eyebrow">{{ module?.english || 'Movement & activity' }}</p>
        <h1>{{ module?.name || '运动健身' }}</h1>
        <p>{{ module?.description || '每一段活动，都值得被好好记录。' }}</p>
      </div>
      <div class="heading-actions">
        <button class="button primary" :disabled="loading || busy || noProfile" @click="openEditor()">
          ＋ 新增运动记录
        </button>
      </div>
    </div>

    <section class="stat-band" aria-label="运动汇总">
      <article class="stat">
        <span>总时长</span>
        <strong>{{ formatMinutes(summary.totalMinutes) }}</strong>
        <small>{{ filterActive ? '当前筛选范围' : '全部记录' }}</small>
      </article>
      <article class="stat">
        <span>记录条数</span>
        <strong>{{ summary.count }} 条</strong>
        <small>平均每次 {{ formatMinutes(summary.averageSession) }}</small>
      </article>
      <article class="stat">
        <span>活跃天数</span>
        <strong>{{ summary.activeDays }} 天</strong>
        <small>日均 {{ formatMinutes(summary.averagePerActiveDay) }}</small>
      </article>
      <article class="stat">
        <span>高强度占比</span>
        <strong>{{ highRatio }}%</strong>
        <small>最长一次 {{ formatMinutes(summary.longest) }}</small>
      </article>
    </section>

    <form class="panel filters" @submit.prevent="load">
      <label>
        <span>开始日期</span>
        <input v-model="filters.date_from" type="date" :disabled="loading || busy" />
      </label>
      <label>
        <span>结束日期</span>
        <input v-model="filters.date_to" type="date" :disabled="loading || busy" />
      </label>
      <div class="filter-actions">
        <button class="button primary" type="submit" :disabled="loading || busy">查询</button>
        <button class="button secondary" type="button" :disabled="loading || busy" @click="applyPreset(7)">
          最近 7 天
        </button>
        <button class="button secondary" type="button" :disabled="loading || busy" @click="applyPreset(30)">
          最近 30 天
        </button>
        <button class="button secondary" type="button" :disabled="loading || busy" @click="clearFilters">
          查看全部
        </button>
      </div>
    </form>

    <p v-if="success" class="notice success" role="status">{{ success }}</p>

    <section v-if="noProfile" class="empty-state">
      <div class="empty-icon"><AppIcon name="profile" /></div>
      <h2>请先建立个人档案</h2>
      <p>运动记录需要归属你的本地健康档案，建档后即可开始记录。</p>
      <RouterLink class="button primary" to="/profile">前往建立档案</RouterLink>
      <button class="button secondary" :disabled="loading" @click="load">建档后重新检查</button>
    </section>

    <div v-else-if="error" class="notice failure" role="alert">
      {{ error }}
      <button class="button secondary" :disabled="loading" @click="load">重试</button>
    </div>

    <template v-else>
      <p v-if="loading" class="loading-hint" role="status">正在加载运动记录…</p>

      <ExerciseRecommendation ref="recommendation" />

      <section class="panel trend-panel">
        <div class="section-heading trend-heading">
          <div>
            <h2>运动时长趋势</h2>
            <p>统计窗口 14 天（{{ trendRange }}），无运动的日期记为 0。</p>
          </div>
          <span class="section-count">{{ filterActive ? '按筛选结果' : '全部记录' }}</span>
        </div>
        <ExerciseTrendChart :points="trend" />
        <p class="intensity-line">
          强度分布（分钟）：低 {{ summary.intensityMinutes.low }} · 中
          {{ summary.intensityMinutes.medium }} · 高 {{ summary.intensityMinutes.high }}
        </p>
      </section>

      <div class="section-heading">
        <div>
          <h2>每日运动明细</h2>
          <p>共 {{ summary.count }} 条记录，覆盖 {{ summary.activeDays }} 天，按日期倒序排列。</p>
        </div>
        <span class="section-count">{{ filterActive ? '已筛选' : '全部' }}</span>
      </div>

      <section v-if="!groups.length" class="empty-state">
        <div class="empty-icon"><AppIcon name="exercise" /></div>
        <h2>还没有运动记录</h2>
        <p>{{ filterActive ? '当前日期范围内没有记录，可以调整日期或查看全部。' : '记录第一次运动，开始积累自己的活动趋势。' }}</p>
        <button class="button primary" :disabled="busy" @click="openEditor()">新增运动记录</button>
        <button v-if="filterActive" class="button secondary" :disabled="loading" @click="clearFilters">
          查看全部记录
        </button>
      </section>

      <div v-else class="day-list">
        <article v-for="group in groups" :key="group.date" class="panel day">
          <header class="day-head">
            <div>
              <h3>{{ group.date }} <span class="weekday">{{ weekdayLabel(group.date) }}</span></h3>
              <p>{{ group.count }} 条记录</p>
            </div>
            <div class="day-total">
              <span>当日合计</span>
              <strong>{{ formatMinutes(group.totalMinutes) }}</strong>
            </div>
          </header>
          <ul class="record-list">
            <li v-for="record in group.items" :key="record.id" class="record">
              <div class="record-main">
                <strong>{{ record.exercise_type }}</strong>
                <span class="tag" :class="`intensity-${record.intensity}`">
                  {{ INTENSITY_LABELS[record.intensity] || record.intensity }}
                </span>
              </div>
              <p class="record-meta">
                {{ record.duration_minutes }} 分钟
                <span v-if="record.notes" class="record-notes"> · {{ record.notes }}</span>
              </p>
              <div class="record-actions">
                <button class="button secondary small" :disabled="busy" @click="openEditor(record)">编辑</button>
                <button class="button danger small" :disabled="busy" @click="askDelete(record)">删除</button>
              </div>
            </li>
          </ul>
        </article>
      </div>
    </template>

    <ExerciseFormDialog ref="editor" :time-zone="timeZone" @saved="onSaved" />

    <dialog ref="confirmation" class="confirm-dialog" aria-labelledby="exercise-delete-title" @cancel="busy && $event.preventDefault()">
      <h2 id="exercise-delete-title">删除运动记录？</h2>
      <p class="delete-copy">
        确认删除 {{ deleting?.record_date }} 的「{{ deleting?.exercise_type }}」（{{ deleting?.duration_minutes }}
        分钟）？删除后无法恢复。
      </p>
      <p v-if="deleteError" class="notice failure" role="alert">{{ deleteError }}</p>
      <div class="dialog-actions">
        <button class="button secondary" :disabled="busy" autofocus @click="closeConfirm">取消</button>
        <button class="button danger" :disabled="busy" @click="remove">
          {{ busy ? '正在删除…' : '确认删除' }}
        </button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.exercise-heading { align-items: flex-start; }
.heading-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
.panel { background: #fff; border: 1px solid #e4e9df; border-radius: 12px; padding: 22px; }
.stat-band { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 20px; }
.stat { background: #fff; border: 1px solid #e4e9df; border-radius: 12px; padding: 18px 20px; display: flex; flex-direction: column; gap: 6px; }
.stat span { font-size: 12px; color: #7d8a80; }
.stat strong { font-size: 22px; font-weight: 600; color: var(--green); font-variant-numeric: tabular-nums; }
.stat small { font-size: 11px; color: #8b968a; }
.filters { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; margin-bottom: 22px; }
label { display: flex; flex-direction: column; gap: 7px; font-size: 13px; }
input, select, textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid #cddace;
  border-radius: 7px;
  padding: 9px 12px;
  font: inherit;
  color: #273e36;
  background: #fff;
}
.filters input { width: 170px; }
.filter-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.notice { margin: 0 0 18px; padding: 12px 15px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.success { background: #eaf3ed; color: #2c5f4b; }
.failure { background: #fff0ec; color: #983b2d; }
.loading-hint { font-size: 13px; color: #7a8779; margin-bottom: 14px; }
.trend-panel { margin-bottom: 26px; }
.trend-heading { margin: 0 0 18px; }
.intensity-line { margin-top: 16px; padding-top: 12px; border-top: 1px dashed #e3ebdf; font-size: 12px; color: #7a8779; }
.day-list { display: flex; flex-direction: column; gap: 14px; }
.day-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-bottom: 14px; border-bottom: 1px solid #eef2ec; }
.day-head h3 { font-size: 16px; font-weight: 600; }
.weekday { margin-left: 6px; font-size: 12px; font-weight: 400; color: #8b968a; }
.day-head p { margin-top: 4px; font-size: 12px; color: #8b968a; }
.day-total { text-align: right; flex-shrink: 0; }
.day-total span { display: block; font-size: 11px; color: #8b968a; }
.day-total strong { font-size: 17px; color: var(--green); }
.record-list { list-style: none; margin: 0; padding: 0; }
.record { display: flex; align-items: center; gap: 16px; padding: 12px 0; border-bottom: 1px solid #f2f5f0; }
.record:last-child { border-bottom: 0; padding-bottom: 0; }
.record-main { display: flex; align-items: center; gap: 10px; min-width: 0; }
.record-main strong { font-size: 14px; font-weight: 600; }
.record-meta { flex: 1; min-width: 0; margin: 0; font-size: 13px; color: #6f7d70; overflow-wrap: anywhere; }
.record-notes { color: #8b968a; }
.record-actions { display: flex; gap: 8px; flex-shrink: 0; }
.tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; white-space: nowrap; }
.intensity-low { background: #eaf3ed; color: #3f7a63; }
.intensity-medium { background: #fbf2e3; color: #97702f; }
.intensity-high { background: #fdeceb; color: #a8443a; }
.button.small { min-height: 30px; padding: 5px 12px; font-size: 12px; }
.empty-state .button + .button { margin-left: 10px; }
.button.danger { background: #fff1ed; border-color: #ecd1c8; color: #a04431; }
.button.danger:hover { background: #fbe3da; }
.confirm-dialog {
  width: min(440px, calc(100% - 32px));
  padding: 26px;
  border: 1px solid #dbe5d6;
  border-radius: 14px;
  color: #273e36;
  background: #fff;
}
.confirm-dialog::backdrop { background: #18372b66; }
.confirm-dialog h2 { font-size: 20px; margin-bottom: 12px; }
.delete-copy { font-size: 13px; color: #5f6f61; overflow-wrap: anywhere; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px; }
@media (max-width: 1020px) {
  .stat-band { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .heading-actions { width: 100%; justify-content: flex-start; }
  .filters label { width: 100%; }
  .filters input { width: 100%; }
  .record { flex-wrap: wrap; gap: 8px; }
  .record-meta { flex-basis: 100%; order: 3; }
  .record-actions { margin-left: auto; }
  .day-head { align-items: flex-start; }
  .empty-state .button + .button { margin-left: 0; }
  .panel { padding: 17px; }
}
</style>
