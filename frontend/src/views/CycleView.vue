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

const activeTab = ref('cycle')

const cycleForm = ref({
  start_date: '',
  end_date: '',
  flow_level: 'medium',
  symptoms: [],
  notes: '',
})

const dailyForm = ref({
  record_date: new Date().toISOString().split('T')[0],
  mood: [],
  extras: [],
  notes: '',
})

const flowOptions = [
  { label: '少量', value: 'light' },
  { label: '中等', value: 'medium' },
  { label: '较多', value: 'heavy' }
]

const customTags = ref([])

const symptomGroups = ref([
  {
    title: '全身',
    items: [
      { label: '一切正常', icon: 'smile' }, { label: '疲劳', icon: 'battery' },
      { label: '抽筋', icon: 'zap' }, { label: '浮肿', icon: 'droplet' }
    ]
  },
  {
    title: '头部',
    items: [
      { label: '头痛', icon: 'brain' }, { label: '呕吐', icon: 'frown' },
      { label: '失眠', icon: 'moon' }, { label: '眩晕', icon: 'sun' }
    ]
  },
  {
    title: '腹部',
    items: [
      { label: '腹部胀痛', icon: 'circle' }, { label: '腹部绞痛', icon: 'activity' },
      { label: '腹泻', icon: 'arrow-down' }, { label: '小腹坠痛', icon: 'thermometer' }
    ]
  },
  {
    title: '其他',
    items: [
      { label: '乳房胀痛', icon: 'heart' }, { label: '腰背酸痛', icon: 'activity' },
      { label: '潮热', icon: 'thermometer' }, { label: '点滴出血', icon: 'droplet' }
    ]
  }
])

const moodOptions = ref([
  { label: '兴奋', icon: 'star' }, { label: '开心', icon: 'smile' },
  { label: '放松', icon: 'cloud' }, { label: '敏感', icon: 'alert' },
  { label: '焦虑', icon: 'activity' }, { label: '生气', icon: 'zap' },
  { label: '压抑', icon: 'arrow-down' }, { label: '悲伤', icon: 'frown' }
])

const extraGroups = ref([
  { title: '性行为', items: [{ label: '无', icon: 'slash' }, { label: '保护性行为', icon: 'shield' }, { label: '无保护性行为', icon: 'alert' }] },
  { title: '私处分泌物', items: [{ label: '干燥', icon: 'circle' }, { label: '粘稠', icon: 'droplet' }, { label: '蛋清状', icon: 'egg' }, { label: '水状', icon: 'droplet' }, { label: '乳液状', icon: 'cloud' }] },
  { title: '皮肤', items: [{ label: '好', icon: 'star' }, { label: '出油', icon: 'droplet' }, { label: '干燥', icon: 'wind' }, { label: '粉刺', icon: 'circle' }, { label: '冒痘', icon: 'target' }] }
])

// 核心修复点：通过传入 groupTitle 来区分不同分类下的相同标签
function toggleTag(list, item, groupTitle = '') {
  const rawLabel = typeof item === 'string' ? item : item.label
  // 如果有分类标题（比如"私处分泌物"），就拼上前缀。如果是"心情"就不拼。
  const target = groupTitle ? `${groupTitle}:${rawLabel}` : rawLabel
  const index = list.indexOf(target)
  if (index > -1) list.splice(index, 1)
  else list.push(target)
}

// 判断是否选中
function isActive(list, item, groupTitle = '') {
  const rawLabel = typeof item === 'string' ? item : item.label
  const target = groupTitle ? `${groupTitle}:${rawLabel}` : rawLabel
  return list.includes(target)
}

function addCustomTag(list, itemsArray, groupTitle = '') {
  const newTag = prompt('请输入自定义选项：')
  if (newTag && newTag.trim() !== '') {
    const cleanTag = newTag.trim()
    if (!itemsArray.some(i => (typeof i === 'string' ? i : i.label) === cleanTag)) {
      itemsArray.push({ label: cleanTag, icon: 'tag' })
      customTags.value.push(cleanTag)
    }
    // 自定义也加上前缀
    const target = groupTitle ? `${groupTitle}:${cleanTag}` : cleanTag
    if (!list.includes(target)) list.push(target)
  }
}

function removeCustomTag(list, itemsArray, tagToRemove, groupTitle = '') {
  const index = itemsArray.findIndex(i => (typeof i === 'string' ? i : i.label) === tagToRemove)
  if (index > -1) itemsArray.splice(index, 1)
  const target = groupTitle ? `${groupTitle}:${tagToRemove}` : tagToRemove
  const selectedIndex = list.indexOf(target)
  if (selectedIndex > -1) list.splice(selectedIndex, 1)
  const customIndex = customTags.value.indexOf(tagToRemove)
  if (customIndex > -1) customTags.value.splice(customIndex, 1)
}

const flowLabels = { light: '少量', medium: '中等', heavy: '较多' }

// ================= 周期逻辑 =================
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
  today.setHours(0, 0, 0, 0); lastStart.setHours(0, 0, 0, 0)
  const daysSince = Math.floor((today - lastStart) / 86400000)
  const cycleLen = prediction.value.avg_cycle_days || 28
  const dayInCycle = ((daysSince % cycleLen) + cycleLen) % cycleLen + 1
  const phase = PHASES.find(p => dayInCycle >= p.range[0] && dayInCycle <= p.range[1]) || PHASES[PHASES.length - 1]
  const cyclesPassed = Math.max(1, Math.ceil((daysSince + 1) / cycleLen))
  const nextStart = new Date(lastStart); nextStart.setDate(nextStart.getDate() + cycleLen * cyclesPassed)
  const daysToNext = Math.ceil((nextStart - today) / 86400000)
  return { phase, dayInCycle, daysToNext: daysToNext >= 0 ? daysToNext : 0 }
})

const careTip = computed(() => {
  if (!phaseInfo.value) return ''
  const { phase, daysToNext } = phaseInfo.value
  if (daysToNext <= 3 && daysToNext > 0) return `距离下次经期还有 ${daysToNext} 天，注意保暖，提前准备好用品。`
  return phase.tip
})

async function loadData() {
  loading.value = true; errorMsg.value = ''
  try {
    records.value = await getCycleRecords()
    try { prediction.value = await getCyclePrediction() } catch { prediction.value = null }
    try { report.value = await getCycleReport() } catch { report.value = null }
  } catch (e) { errorMsg.value = e.message }
  finally { loading.value = false }
}

async function handleCycleSubmit() {
  if (!cycleForm.value.start_date) return errorMsg.value = '请选择开始日期'
  if (cycleForm.value.end_date && cycleForm.value.end_date < cycleForm.value.start_date) {
    return errorMsg.value = '结束日期不能早于开始日期'
  }
  try {
    const submitData = {
      ...cycleForm.value,
      symptoms: cycleForm.value.symptoms.join('、'),
      mood: '', notes: cycleForm.value.notes.trim(),
    }
    await createCycleRecord(submitData)
    cycleForm.value = { start_date: '', end_date: '', flow_level: 'medium', symptoms: [], notes: '' }
    errorMsg.value = ''; await loadData()
  } catch (e) { errorMsg.value = e.message }
}

async function handleDailySubmit() {
  try {
    let finalNotes = dailyForm.value.notes
    if (dailyForm.value.extras.length > 0) {
      // 保存时把前缀去掉，用纯文本保存
      const cleanedExtras = dailyForm.value.extras.map(str => str.split(':').pop())
      finalNotes = `[日常状态: ${cleanedExtras.join('、')}] ` + finalNotes
    }
    const submitData = {
      start_date: dailyForm.value.record_date, end_date: null, flow_level: null,
      symptoms: '', mood: dailyForm.value.mood.join('、'), notes: finalNotes.trim(),
    }
    await createCycleRecord(submitData)
    dailyForm.value.mood = []; dailyForm.value.extras = []; dailyForm.value.notes = ''
    errorMsg.value = ''; await loadData()
  } catch (e) { errorMsg.value = e.message }
}

async function handleDelete(id) {
  if (!confirm('确定删除这条记录吗？')) return
  try { await deleteCycleRecord(id); await loadData() }
  catch (e) { errorMsg.value = e.message }
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
    </div>

    <p v-if="errorMsg" class="error-banner">{{ errorMsg }}</p>

    <div class="tab-nav">
      <button :class="{ active: activeTab === 'cycle' }" @click="activeTab = 'cycle'">经期记录</button>
      <button :class="{ active: activeTab === 'daily' }" @click="activeTab = 'daily'">日常状态</button>
    </div>

    <!-- 经期记录 -->
    <form v-if="activeTab === 'cycle'" class="cycle-form" @submit.prevent="handleCycleSubmit">
      <div class="form-row">
        <label><span>开始日期 *</span><input v-model="cycleForm.start_date" type="date" required /></label>
        <label><span>结束日期</span><input v-model="cycleForm.end_date" type="date" /></label>
      </div>

      <div class="form-group">
        <span class="group-title">流量</span>
        <div class="tag-container">
          <button type="button" v-for="opt in flowOptions" :key="opt.value" class="tag-btn" :class="{ active: cycleForm.flow_level === opt.value }" @click="cycleForm.flow_level = opt.value">
            {{ opt.label }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <span class="group-title">身体症状 (可多选)</span>
        <div v-for="(group, gIndex) in symptomGroups" :key="group.title" class="sub-group">
          <span class="sub-title">{{ group.title }}</span>
          <div class="tag-container">
            <button type="button" v-for="item in group.items" :key="item.label" class="tag-btn with-svg" :class="{ active: isActive(cycleForm.symptoms, item, '症状') }" @click="toggleTag(cycleForm.symptoms, item, '症状')">
              <svg class="svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path v-if="item.icon === 'smile'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm-3-7c1 1 2.5 1.5 3 1.5s2-.5 3-1.5M9 9h.01M15 9h.01"/>
                <path v-if="item.icon === 'battery'" d="M5 18H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2M9 18v2m6-2v2"/>
                <path v-if="item.icon === 'zap'" d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                <path v-if="item.icon === 'droplet'" d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
                <path v-if="item.icon === 'brain'" d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2zM14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2z"/>
                <path v-if="item.icon === 'frown'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm-3-7c1-1 2.5-1.5 3-1.5s2 .5 3 1.5M9 9h.01M15 9h.01"/>
                <path v-if="item.icon === 'moon'" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                <path v-if="item.icon === 'sun'" d="M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-15v2m0 16v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M2 12h2m16 0h2M4.22 19.78l1.42-1.42m12.72-12.72l1.42-1.42"/>
                <path v-if="item.icon === 'circle'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                <path v-if="item.icon === 'activity'" d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                <path v-if="item.icon === 'arrow-down'" d="M12 5v14m-7-7l7 7 7-7"/>
                <path v-if="item.icon === 'thermometer'" d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
                <path v-if="item.icon === 'heart'" d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                <path v-if="item.icon === 'tag'" d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82zM7 7h.01"/>
              </svg>
              {{ item.label }}
              <span v-if="customTags.includes(item.label)" class="del-icon" @click.stop="removeCustomTag(cycleForm.symptoms, group.items, item.label, '症状')">×</span>
            </button>
            <button type="button" class="tag-btn custom-btn" @click="addCustomTag(cycleForm.symptoms, symptomGroups[gIndex].items, '症状')">
              + 自定义
            </button>
          </div>
        </div>
      </div>

      <div class="form-group">
        <label><span class="group-title">备注</span><input v-model="cycleForm.notes" type="text" placeholder="补充信息..." /></label>
      </div>

      <button class="button primary" type="submit">保存经期记录 <AppIcon name="check" /></button>
    </form>

    <!-- 日常状态 -->
    <form v-if="activeTab === 'daily'" class="cycle-form" @submit.prevent="handleDailySubmit">
      <div class="form-row">
        <label><span>记录日期 *</span><input v-model="dailyForm.record_date" type="date" required /></label>
      </div>

      <div class="form-group">
        <span class="group-title">心情记录 (可多选)</span>
        <div class="tag-container">
          <button type="button" v-for="item in moodOptions" :key="item.label" class="tag-btn with-svg" :class="{ active: isActive(dailyForm.mood, item, '心情') }" @click="toggleTag(dailyForm.mood, item, '心情')">
             <svg class="svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path v-if="item.icon === 'star'" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                <path v-if="item.icon === 'smile'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm-3-7c1 1 2.5 1.5 3 1.5s2-.5 3-1.5M9 9h.01M15 9h.01"/>
                <path v-if="item.icon === 'cloud'" d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                <path v-if="item.icon === 'alert'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm0-6v-6m0-4h.01"/>
                <path v-if="item.icon === 'activity'" d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                <path v-if="item.icon === 'zap'" d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                <path v-if="item.icon === 'arrow-down'" d="M12 5v14m-7-7l7 7 7-7"/>
                <path v-if="item.icon === 'frown'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm-3-7c1-1 2.5-1.5 3-1.5s2 .5 3 1.5M9 9h.01M15 9h.01"/>
                <path v-if="item.icon === 'tag'" d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82zM7 7h.01"/>
             </svg>
            {{ item.label }}
            <span v-if="customTags.includes(item.label)" class="del-icon" @click.stop="removeCustomTag(dailyForm.mood, moodOptions, item.label, '心情')">×</span>
          </button>
          <button type="button" class="tag-btn custom-btn" @click="addCustomTag(dailyForm.mood, moodOptions, '心情')">+ 自定义</button>
        </div>
      </div>

      <div v-for="(group, gIndex) in extraGroups" :key="group.title" class="form-group">
        <span class="group-title">{{ group.title }}</span>
        <div class="tag-container">
          <!-- 传入 group.title 作为分类隔离 -->
          <button type="button" v-for="item in group.items" :key="item.label" class="tag-btn with-svg" :class="{ active: isActive(dailyForm.extras, item, group.title) }" @click="toggleTag(dailyForm.extras, item, group.title)">
            <svg class="svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
               <path v-if="item.icon === 'slash'" d="M4 4l16 16M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
               <path v-if="item.icon === 'shield'" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
               <path v-if="item.icon === 'alert'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm0-6v-6m0-4h.01"/>
               <path v-if="item.icon === 'circle'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
               <path v-if="item.icon === 'droplet'" d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
               <path v-if="item.icon === 'egg'" d="M12 22c4.418 0 8-3.582 8-8s-3.582-8-8-8-8 3.582-8 8 3.582 8 8 8z"/>
               <path v-if="item.icon === 'cloud'" d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
               <path v-if="item.icon === 'star'" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
               <path v-if="item.icon === 'wind'" d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
               <path v-if="item.icon === 'target'" d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm0-4a6 6 0 1 0 0-12 6 6 0 0 0 0 12zm0-4a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>
               <path v-if="item.icon === 'tag'" d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82zM7 7h.01"/>
            </svg>
            {{ item.label }}
            <span v-if="customTags.includes(item.label)" class="del-icon" @click.stop="removeCustomTag(dailyForm.extras, group.items, item.label, group.title)">×</span>
          </button>
          <button type="button" class="tag-btn custom-btn" @click="addCustomTag(dailyForm.extras, extraGroups[gIndex].items, group.title)">+ 自定义</button>
        </div>
      </div>

      <div class="form-group">
        <label><span class="group-title">备注</span><input v-model="dailyForm.notes" type="text" placeholder="补充信息..." /></label>
      </div>

      <button class="button primary" type="submit">保存日常状态 <AppIcon name="check" /></button>
    </form>

    <!-- 周期预测 / 关怀 / 报告 -->
    <div v-if="prediction && prediction.predicted_next" class="prediction-card">
      <h3>周期预测</h3>
      <p>上次经期：{{ prediction.last_start }}</p>
      <p>平均周期：{{ prediction.avg_cycle_days }} 天</p>
      <p>排卵日：{{ prediction.ovulation_date }}</p>
      <p>易孕期：{{ prediction.fertile_start }} ~ {{ prediction.fertile_end }}</p>
      <p>预测下次经期：<strong>{{ prediction.predicted_next }}</strong></p>
      <div v-if="phaseInfo" class="phase-box">
        <p>当前周期第 <strong>{{ phaseInfo.dayInCycle }}</strong> 天，处于 <strong>{{ phaseInfo.phase.name }}</strong></p>
        <p v-if="phaseInfo.daysToNext > 0">距离下次经期还有 <strong>{{ phaseInfo.daysToNext }}</strong> 天</p>
      </div>
    </div>
    <p v-else class="hint">至少记录两次经期后，这里会显示周期预测。</p>

    <div v-if="careTip" class="care-card">
      <span class="care-icon"><AppIcon name="cycle" /></span>
      <p>{{ careTip }}</p>
    </div>

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
          <span v-if="r.flow_level" class="tag">{{ flowLabels[r.flow_level] || '—' }}</span>
          <span v-else class="tag" style="background:#f5f5f7; color:#888;">日常</span>
        </div>
        <p v-if="r.symptoms"><span style="color:#888;">症状：</span>{{ r.symptoms }}</p>
        <p v-if="r.mood"><span style="color:#888;">情绪：</span>{{ r.mood }}</p>
        <p v-if="r.notes" class="note">{{ r.notes }}</p>
        <button class="button ghost" @click="handleDelete(r.id)">删除</button>
      </article>
    </section>

    <section v-else class="empty-state">
      <div class="empty-icon"><AppIcon name="cycle" /></div>
      <h2>还没有记录</h2>
      <p>填写上方表单，保存第一条记录。</p>
    </section>
  </div>
</template>

<style scoped>
/* 粉色主题样式 */
.tab-nav { display: flex; gap: 1rem; margin-bottom: 1.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
.tab-nav button { padding: 0.5rem 1.5rem; border: none; background: transparent; font-size: 1rem; cursor: pointer; border-radius: 20px; color: #666; transition: 0.2s; }
.tab-nav button.active { background: #fde8ec; color: #b23a52; font-weight: 500; }

.error-banner { margin: 1rem 0; padding: 0.75rem 1rem; background: #fde8ec; color: #b23a52; border-radius: 8px; font-size: 0.9rem; }
.cycle-form { display: flex; flex-direction: column; gap: 1.5rem; margin: 1rem 0 2rem; padding: 2rem; background: #fff; border-radius: 16px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }
.form-row { display: flex; gap: 1rem; }
.form-row label { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.95rem; }
.form-group { display: flex; flex-direction: column; gap: 0.75rem; }
.sub-group { margin-bottom: 0.5rem; }
.sub-title { font-size: 0.85rem; color: #888; display: block; margin-bottom: 0.5rem; }
.group-title { font-size: 0.95rem; color: #333; font-weight: 500; margin-bottom: 0.2rem; }
.cycle-form input { padding: 0.6rem 0.8rem; border: 1px solid #eee; border-radius: 8px; font-size: 0.95rem; background: #fafafa; }
.cycle-form input:focus { outline: none; border-color: #e8a5b5; background: #fff; }

.tag-container { display: flex; flex-wrap: wrap; gap: 1rem; }

.tag-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0.6rem 1.2rem;
  border: 1px solid #f0e6ea;
  border-radius: 12px;
  background: #fbf9fa;
  color: #666;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 80px;
}
.tag-btn:hover { background: #f5eff1; }
.tag-btn.active {
  background: #fde8ec;
  border-color: #f3c6d0;
  color: #b23a52;
  font-weight: 500;
}

.with-svg {
  padding-left: 0.8rem;
}
.svg-icon {
  width: 16px;
  height: 16px;
  opacity: 0.8;
}
.tag-btn.active .svg-icon {
  opacity: 1;
}

.custom-btn {
  border-style: dashed;
  background: transparent;
  color: #999;
}
.custom-btn:hover {
  color: #b23a52;
  border-color: #f3c6d0;
}
.del-icon {
  font-size: 1.2rem;
  line-height: 1;
  margin-left: 4px;
  color: #d98ba0;
  cursor: pointer;
}
.del-icon:hover {
  color: #b23a52;
}

.prediction-card { padding: 1.25rem 1.5rem; background: #fdf2f4; border-radius: 12px; margin-bottom: 1.5rem; }
.prediction-card h3 { margin: 0 0 0.5rem; }
.prediction-card p { margin: 0.25rem 0; font-size: 0.9rem; }
.phase-box { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px dashed #f3c6d0; }
.phase-box p { margin: 0.25rem 0; }
.hint { color: #888; font-size: 0.9rem; margin-bottom: 1.5rem; }
.care-card { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; margin-bottom: 1.5rem; background: #fff7f9; border-left: 3px solid #e8a5b5; border-radius: 8px; }
.care-card p { margin: 0; font-size: 0.9rem; color: #6b4a52; }
.care-icon { color: #d98ba0; flex-shrink: 0; }
.report-card { padding: 1.25rem 1.5rem; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); margin-bottom: 1.5rem; }
.report-card h3 { margin: 0 0 1rem; }
.report-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; }
.report-grid div { display: flex; flex-direction: column; gap: 0.25rem; }
.report-grid span { font-size: 0.8rem; color: #888; }
.report-grid strong { font-size: 1.1rem; color: #b23a52; }
.cycle-list { display: flex; flex-direction: column; gap: 0.75rem; }
.cycle-item { position: relative; padding: 1rem 1.25rem; background: #fff; border-radius: 10px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); }
.cycle-item .tag { margin-left: 0.5rem; padding: 0.15rem 0.5rem; background: #fde8ec; color: #b23a52; border-radius: 4px; font-size: 0.8rem; }
.cycle-item p { margin: 0.35rem 0 0; font-size: 0.9rem; color: #555; }
.cycle-item .note { color: #b23a52; font-size: 0.85rem; margin-top: 0.5rem; background: #fdfafb; padding: 0.5rem; border-radius: 6px; }
.cycle-item button { position: absolute; top: 1rem; right: 1rem; }
</style>
