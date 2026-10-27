<script setup>
import { ref, onMounted, watch } from 'vue'

// ================= 1. 运动记录与图表逻辑 =================
const newRecord = ref({ type: '跑步', duration: 30, intensity: '中等' })
const historyRecords = ref([
  { id: 1, type: '跑步', duration: 30, intensity: '中等', calories: 300, date: '2026-10-10' },
  { id: 2, type: '游泳', duration: 45, intensity: '高', calories: 700, date: '2026-10-11' },
])
const chartRef = ref(null)
let myChart = null

const renderChart = () => {
  if (!chartRef.value) return
  if (myChart) myChart.dispose()
  myChart = echarts.init(chartRef.value)
  const dates = historyRecords.value.map(item => item.date)
  const calories = historyRecords.value.map(item => item.calories)
  const option = {
    title: { text: '消耗趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: 'kcal' },
    series: [{ data: calories, type: 'bar', itemStyle: { color: '#4CAF50' } }]
  }
  myChart.setOption(option)
}

onMounted(() => renderChart())
watch(historyRecords, () => renderChart(), { deep: true })

const addRecord = () => {
  let baseRate = newRecord.value.type === '游泳' ? 12 : newRecord.value.type === '瑜伽' ? 4 : 10
  let multiplier = newRecord.value.intensity === '低' ? 0.8 : newRecord.value.intensity === '高' ? 1.3 : 1
  const calories = Math.round(newRecord.value.duration * baseRate * multiplier)
  historyRecords.value.unshift({
    id: Date.now(), type: newRecord.value.type, duration: newRecord.value.duration,
    intensity: newRecord.value.intensity, calories: calories,
    date: new Date().toISOString().split('T')[0]
  })
}

// ================= 2. 训练计划生成逻辑 =================
const planGoal = ref('减脂') // 目标：减脂/增肌/塑形
const planEquipment = ref('徒手') // 器械：徒手/哑铃/健身房
const generatedPlan = ref([]) // 生成的动作列表

// 动作库字典（包含动作名、组数、次数、适用目标和器械）
const exerciseLibrary = {
  减脂: {
    徒手: ['开合跳 3组x30秒', '波比跳 3组x12次', '高抬腿 3组x30秒', '原地慢跑 10分钟'],
    哑铃: ['哑铃深蹲推举 4组x15次', '哑铃壶铃摇摆 4组x20次', '哑铃划船 3组x12次'],
    健身房: ['跑步机爬坡 20分钟', '划船机 15分钟', '动感单车 20分钟']
  },
  增肌: {
    徒手: ['标准俯卧撑 4组x力竭', '引体向上 4组x力竭', '保加利亚分腿蹲 3组x15次'],
    哑铃: ['哑铃卧推 4组x10次', '哑铃硬拉 4组x10次', '哑铃弯举 3组x12次'],
    健身房: ['杠铃深蹲 4组x8次', '杠铃卧推 4组x8次', '高位下拉 3组x12次']
  },
  塑形: {
    徒手: ['平板支撑 3组x60秒', '臀桥 3组x20次', '死虫式 3组x15次'],
    哑铃: ['哑铃侧平举 4组x15次', '哑铃俄罗斯转体 3组x20次', '哑铃箭步蹲 3组x12次'],
    健身房: ['坐姿推胸 3组x15次', '坐姿划船 3组x15次', '腿举 3组x15次']
  }
}

// 生成计划的方法
const generatePlan = () => {
  // 根据用户选择的目标和器械，从字典里取出对应数组
  generatedPlan.value = exerciseLibrary[planGoal.value][planEquipment.value]
}
</script>

<template>
  <div class="exercise-container">
    <h2>🏃 运动健身管理</h2>
    
    <!-- 1. 训练计划生成区 -->
    <div class="card plan-section">
      <h3>🎯 智能训练计划生成</h3>
      <div class="form-row">
        <div class="form-group">
          <label>健身目标：</label>
          <select v-model="planGoal">
            <option value="减脂">减脂</option>
            <option value="增肌">增肌</option>
            <option value="塑形">塑形</option>
          </select>
        </div>
        <div class="form-group">
          <label>可用器械：</label>
          <select v-model="planEquipment">
            <option value="徒手">徒手（无器械）</option>
            <option value="哑铃">哑铃（家庭）</option>
            <option value="健身房">健身房器械</option>
          </select>
        </div>
        <button class="submit-btn blue-btn" @click="generatePlan">生成我的计划</button>
      </div>
      
      <!-- 展示生成的计划 -->
      <div v-if="generatedPlan.length > 0" class="plan-result">
        <h4>为你定制的【{{ planGoal }}】计划（{{ planEquipment }}）：</h4>
        <ul>
          <li v-for="(action, index) in generatedPlan" :key="index">{{ action }}</li>
        </ul>
      </div>
    </div>

    <!-- 2. 运动记录录入区 -->
    <div class="card form-section">
      <h3>记录今日运动</h3>
      <div class="form-row">
        <div class="form-group">
          <label>运动类型：</label>
          <select v-model="newRecord.type">
            <option value="跑步">跑步</option>
            <option value="游泳">游泳</option>
            <option value="瑜伽">瑜伽</option>
            <option value="骑行">骑行</option>
          </select>
        </div>
        <div class="form-group">
          <label>运动时长（分钟）：</label>
          <input type="number" v-model="newRecord.duration" min="1" />
        </div>
        <div class="form-group">
          <label>运动强度：</label>
          <select v-model="newRecord.intensity">
            <option value="低">低强度</option>
            <option value="中等">中等强度</option>
            <option value="高">高强度</option>
          </select>
        </div>
        <button class="submit-btn" @click="addRecord">添加记录</button>
      </div>
    </div>

    <!-- 3. 图表与历史记录 -->
    <div class="data-section">
      <div class="card chart-card">
        <div ref="chartRef" style="width: 100%; height: 300px;"></div>
      </div>
      <div class="card table-card">
        <h3>运动打卡明细</h3>
        <table class="record-table">
          <thead>
            <tr><th>日期</th><th>类型</th><th>时长</th><th>消耗</th></tr>
          </thead>
          <tbody>
            <tr v-for="record in historyRecords" :key="record.id">
              <td>{{ record.date }}</td>
              <td>{{ record.type }}</td>
              <td>{{ record.duration }}分</td>
              <td class="highlight">{{ record.calories }}kcal</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.exercise-container { padding: 20px; max-width: 1000px; margin: 0 auto; font-family: sans-serif; }
.card { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.form-row { display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }
.form-group { display: flex; flex-direction: column; }
.form-group label { margin-bottom: 5px; font-size: 14px; color: #555; }
.form-group input, .form-group select { padding: 8px; width: 150px; border: 1px solid #ccc; border-radius: 4px; }
.submit-btn { background: #4CAF50; color: white; border: none; padding: 9px 20px; border-radius: 4px; cursor: pointer; height: fit-content; }
.submit-btn:hover { background: #45a049; }
.blue-btn { background: #2196F3; }
.blue-btn:hover { background: #1976D2; }

/* 计划展示区样式 */
.plan-result { margin-top: 15px; padding: 15px; background: #f1f8e9; border-radius: 6px; border-left: 4px solid #4CAF50; }
.plan-result h4 { margin-top: 0; color: #2e7d32; }
.plan-result ul { margin-bottom: 0; padding-left: 20px; }
.plan-result li { margin-bottom: 8px; line-height: 1.5; color: #333; }

.data-section { display: flex; gap: 20px; }
.chart-card, .table-card { flex: 1; }
.record-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.record-table th, .record-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
.highlight { color: #ff5722; font-weight: bold; }
</style>
