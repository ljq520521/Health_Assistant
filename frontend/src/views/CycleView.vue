<script setup>
import { ref, computed, onMounted } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import {
  getCycleRecords,
  createCycleRecord,
  deleteCycleRecord,
  getCyclePrediction,
} from '../api/client'

const records = ref([])
const prediction = ref(null)
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

    <div class="page-heading">
      <div>
        <p class="eyebrow">Cycle & wellbeing</p>
        <h1>生理期管理</h1>
        <p>关注身体节奏，也照顾自己的感受。</p>
      </div>
      <span class="outline-badge">成员 E 负责</span>
    </div>

    <p v-if="errorMsg" class="error-banner">{{ errorMsg }}</p>

    <!-- 录入表单 -->
    <section class="module-intro">
      <span class="module-icon large"><AppIcon name="cycle" /></span>
      <div style="flex: 1">
        <h2>记录这次经期</h2>
        <p>填写起止日期、流量、症状与情绪，保存后会显示在下方历史记录中。</p>
      </div>
    </section>

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
      <p>预测下次：<strong>{{ prediction.predicted_next }}</strong></p>
    </div>
    <p v-else class="hint">至少记录两次经期后，这里会显示周期预测。</p>

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
.hint {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
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
