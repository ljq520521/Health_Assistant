<script setup>
import { ref, computed, onMounted } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import {
  getCycleRecords,
  createCycleRecord,
  deleteCycleRecord,
  getCyclePrediction,
  getCycleReport,
} from '../api/client'

const records = ref([])
const prediction = ref(null)
const report = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const form = ref({
  start_date: '',
  end_date: '',
  flow_level: 'medium',
  symptoms: '',
  mood: '',
  notes: '',
})

const flowLabels = { light: '少量', medium: '中等', heavy: '较多' }

const PHASES = [
  { key: 'menstrual', name: '月经期', range: [1, 5], tip: '经期中，多喝温水，避免剧烈运动，注意保暖。' },
  { key: 'follicular', name: '卵泡期', range: [6, 13], tip: '卵泡期，身体状态回升，适合适度运动。' },
  { key: 'ovulation', name: '排卵期', range: [14, 14], tip: '排卵期，注意身体变化，保持规律作息。' },
  { key: 'luteal', name: '黄体期', range: [15, 28], tip: '黄体期，可能出现情绪波动，注意休息与饮食。' },
]

const phaseInfo = computed(() => {
  if (!prediction.value || !prediction.value.last_start || !prediction.value.avg_cycle_days) return null
  const lastStart = new Date(prediction.value.last_start)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  lastStart.setHours(0, 0, 0, 0)
  const daysSince = Math.floor((today - lastStart) / 86400000)
  const cycleLen = prediction.value.avg_cycle_days || 28
  const dayInCycle = ((daysSince % cycleLen) + cycleLen) % cycleLen + 1

  const phase = PHASES.find(p => dayInCycle >= p.range[0] && dayInCycle <= p.range[1])
    || PHASES[PHASES.length - 1]

  const cyclesPassed = Math.max(1, Math.ceil((daysSince + 1) / cycleLen))
  const nextStart = new Date(lastStart)
  nextStart.setDate(nextStart.getDate() + cycleLen * cyclesPassed)
  const daysToNext = Math.ceil((nextStart - today) / 86400000)

  return {
    phase,
    dayInCycle,
    daysToNext: daysToNext >= 0 ? daysToNext : 0,
  }
})

const careTip = computed(() => {
  if (!phaseInfo.value) return ''
  const { phase, daysToNext } = phaseInfo.value
  if (daysToNext <= 3 && daysToNext > 0) {
    return `距离下次经期还有 ${daysToNext} 天，注意保暖，提前准备好用品。`
  }
  return phase.tip
})

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    records.value = await getCycleRecords()
    try {
      prediction.value = await getCyclePrediction()
    } catch {
      prediction.value = null
    }
    try {
      report.value = await getCycleReport()
    } catch {
      report.value = null
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.value.start_date) {
    errorMsg.value = '请选择开始日期'
    return
  }
  if (form.value.end_date && form.value.end_date < form.value.start_date) {
    errorMsg.value = '结束日期不能早于开始日期'
    return
  }
  try {
    await createCycleRecord(form.value)
    form.value = {
      start_date: '', end_date: '', flow_level: 'medium',
      symptoms: '', mood: '', notes: '',
    }
    errorMsg.value = ''
    await loadData()
  } catch (e) {
    errorMsg.value = e.message
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除这条记录吗？')) return
  try {
    await deleteCycleRecord(id)
    await loadData()
  } catch (e) {
    errorMsg.value = e.message
  }
}

onMounted(loadData)
</script>

<template>
  <div class="module-overview rose">
    <RouterLink class="back-link" to="/">← 返回总览</RouterLink>

    <!-- 删除了右上角的成员 E 负责 -->
    <div class="page-heading">
      <div>
        <p class="eyebrow">Cycle & wellbeing</p>
        <h1>生理期管理</h1>
        <p>关注身体节奏，也照顾自己的感受。</p>
      </div>
    </div>

    <p v-if="errorMsg" class="error-banner">{{ errorMsg }}</p>

    <!-- 删除了原本的红色图标说明，直接展示表单 -->
    <form class="cycle-form" @submit.prevent="handleSubmit">
      <label>
        <span>开始日期 *</span>
        <input v-model="form.start_date" type="date" required />
      </label>
      <label>
        <span>结束日期</span>
        <input v-model="form.end_date" type="date" />
      </label>
      <label>
        <span>流量</span>
        <select v-model="form.flow_level">
          <option value="light">少量</option>
          <option value="medium">中等</option>
          <option value="heavy">较多</option>
        </select>
      </label>
      <label>
        <span>症状</span>
        <input v-model="form.symptoms" type="text" placeholder="如：腰酸、腹痛" />
      </label>
      <label>
        <span>情绪</span>
        <input v-model="form.mood" type="text" placeholder="如：平稳、烦躁" />
      </label>
      <label>
        <span>备注</span>
        <input v-model="form.notes" type="text" placeholder="可选" />
      </label>
      <button class="button primary" type="submit">
        保存记录 <AppIcon name="check" />
      </button>
    </form>

    <!-- 周期预测 -->
    <div v-if="prediction && prediction.predicted_next" class="prediction-card">
      <h3>周期预测</h3>
      <p>上次经期：{{ prediction.last_start }}</p>
      <p>平均周期：{{ prediction.avg_cycle_days }} 天</p>
      <p>排卵日：{{ prediction.ovulation_date }}</p>
      <p>易孕期：{{ prediction.fertile_start }} ~ {{ prediction.fertile_end }}</p>
      <p>预测下次经期：<strong>{{ prediction.predicted_next }}</strong></p>

      <div v-if="phaseInfo" class="phase-box">
        <p>当前周期第 <strong>{{ phaseInfo.dayInCycle }}</strong> 天，处于
          <strong>{{ phaseInfo.phase.name }}</strong>
        </p>
        <p v-if="phaseInfo.daysToNext > 0">距离下次经期还有
          <strong>{{ phaseInfo.daysToNext }}</strong> 天
        </p>
      </div>
    </div>
    <p v-else class="hint">至少记录两次经期后，这里会显示周期预测。</p>

    <!-- 关怀提醒 -->
    <div v-if="careTip" class="care-card">
      <span class="care-icon"><AppIcon name="cycle" /></span>
      <p>{{ careTip }}</p>
    </div>

    <!-- 周期报告 -->
    <div v-if="report && report.total_records >= 2" class="report-card">
      <h3>周期报告</h3>
      <div class="report-grid">
        <div><span>记录次数</span><strong>{{ report.total_records }}</strong></div>
        <div><span>平均周期</span><strong>{{ report.avg_cycle_days }} 天</strong></div>
        <div><span>最短周期</span><strong>{{ report.shortest_cycle }} 天</strong></div>
        <div><span>最长周期</span><strong>{{ report.longest_cycle }} 天</strong></div>
        <div><span>平均经期</span><strong>{{ report.avg_period_length }} 天</strong></div>
        <div><span>规律性</span><strong>{{ report.regularity }}</strong></div>
      </div>
    </div>

    <!-- 历史记录 -->
    <div class="section-heading">
      <div>
        <h2>历史记录</h2>
        <p>共 {{ records.length }} 条</p>
      </div>
    </div>

    <section v-if="records.length" class="cycle-list">
      <article v-for="r in records" :key="r.id" class="cycle-item">
        <div>
          <strong>{{ r.start_date }}</strong>
          <span v-if="r.end_date"> ~ {{ r.end_date }}</span>
          <span class="tag">{{ flowLabels[r.flow_level] || '—' }}</span>
        </div>
        <p v-if="r.symptoms || r.mood">
          <span v-if="r.symptoms">症状：{{ r.symptoms }}</span>
          <span v-if="r.mood"> 情绪：{{ r.mood }}</span>
        </p>
        <p v-if="r.notes" class="note">{{ r.notes }}</p>
        <button class="button ghost" @click="handleDelete(r.id)">删除</button>
      </article>
    </section>

    <section v-else class="empty-state">
      <div class="empty-icon"><AppIcon name="cycle" /></div>
      <h2>还没有经期记录</h2>
      <p>填写上方表单，保存第一条记录。</p>
    </section>
  </div>
</template>

<style scoped>
.error-banner {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background: #fde8ec;
  color: #b23a52;
  border-radius: 8px;
  font-size: 0.9rem;
}
.cycle-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.cycle-form label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
}
.cycle-form input,
.cycle-form select {
  padding: 0.5rem 0.65rem;
  border: 1px solid #e3e3e3;
  border-radius: 6px;
  font-size: 0.9rem;
}
.cycle-form button {
  align-self: end;
  grid-column: 1 / -1;
  width: fit-content;
}
.prediction-card {
  padding: 1.25rem 1.5rem;
  background: #fdf2f4;
  border-radius: 12px;
  margin-bottom: 1.5rem;
}
.prediction-card h3 {
  margin: 0 0 0.5rem;
}
.prediction-card p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
}
.phase-box {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #f3c6d0;
}
.phase-box p {
  margin: 0.25rem 0;
}
.hint {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}
.care-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  background: #fff7f9;
  border-left: 3px solid #e8a5b5;
  border-radius: 8px;
}
.care-card p {
  margin: 0;
  font-size: 0.9rem;
  color: #6b4a52;
}
.care-icon {
  color: #d98ba0;
  flex-shrink: 0;
}
.report-card {
  padding: 1.25rem 1.5rem;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  margin-bottom: 1.5rem;
}
.report-card h3 {
  margin: 0 0 1rem;
}
.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}
.report-grid div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.report-grid span {
  font-size: 0.8rem;
  color: #888;
}
.report-grid strong {
  font-size: 1.1rem;
  color: #b23a52;
}
.cycle-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.cycle-item {
  position: relative;
  padding: 1rem 1.25rem;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.cycle-item .tag {
  margin-left: 0.5rem;
  padding: 0.15rem 0.5rem;
  background: #fde8ec;
  color: #b23a52;
  border-radius: 4px;
  font-size: 0.8rem;
}
.cycle-item p {
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
  color: #555;
}
.cycle-item .note {
  color: #888;
}
.cycle-item button {
  position: absolute;
  top: 1rem;
  right: 1rem;
}
</style>
