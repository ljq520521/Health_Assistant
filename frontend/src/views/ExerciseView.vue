<script setup>
import { ref, onMounted, watch } from 'vue'

// 表单数据
const newRecord = ref({
  type: '跑步',
  duration: 30,
  intensity: '中等'
})

// 历史记录列表
const historyRecords = ref([
  { id: 1, type: '跑步', duration: 30, intensity: '中等', calories: 300, date: '2026-10-10' },
  { id: 2, type: '游泳', duration: 45, intensity: '高', calories: 700, date: '2026-10-11' },
  { id: 3, type: '瑜伽', duration: 60, intensity: '低', calories: 180, date: '2026-10-12' },
])

// 图表的 DOM 容器引用
const chartRef = ref(null)
let myChart = null

// 初始化并渲染图表
const renderChart = () => {
  if (!chartRef.value) return
  
  // 销毁旧实例，防止重复渲染
  if (myChart) myChart.dispose()
  
  myChart = echarts.init(chartRef.value)
  
  // 提取日期和卡路里数据
  const dates = historyRecords.value.map(item => item.date)
  const calories = historyRecords.value.map(item => item.calories)

  const option = {
    title: { text: '近阶段卡路里消耗趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: { 
      type: 'category', 
      data: dates,
      name: '日期'
    },
    yAxis: { 
      type: 'value',
      name: '消耗(kcal)'
    },
    series: [
      {
        data: calories,
        type: 'bar', // 柱状图，你也可以改成 'line' 变折线图
        itemStyle: { color: '#4CAF50' }
      }
    ]
  }
  myChart.setOption(option)
}

// 页面加载后渲染图表
onMounted(() => {
  renderChart()
})

// 监听记录变化，每次添加新记录就刷新图表
watch(historyRecords, () => {
  renderChart()
}, { deep: true })

// 添加记录的方法
const addRecord = () => {
  let baseRate = 10
  if (newRecord.value.type === '游泳') baseRate = 12
  if (newRecord.value.type === '瑜伽') baseRate = 4
  if (newRecord.value.type === '骑行') baseRate = 8

  let multiplier = 1
  if (newRecord.value.intensity === '低') multiplier = 0.8
  if (newRecord.value.intensity === '高') multiplier = 1.3

  const calories = Math.round(newRecord.value.duration * baseRate * multiplier)

  historyRecords.value.unshift({
    id: Date.now(),
    type: newRecord.value.type,
    duration: newRecord.value.duration,
    intensity: newRecord.value.intensity,
    calories: calories,
    date: new Date().toISOString().split('T')[0]
  })
}
</script>

<template>
  <div class="exercise-container">
    <h2>🏃 运动健身管理</h2>
    
    <!-- 上方：打卡录入区 -->
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

    <!-- 下方：图表与历史记录 -->
    <div class="data-section">
      <!-- 左边放图表 -->
      <div class="card chart-card">
        <div ref="chartRef" style="width: 100%; height: 300px;"></div>
      </div>

      <!-- 右边放表格 -->
      <div class="card table-card">
        <h3>运动打卡明细</h3>
        <table class="record-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>运动类型</th>
              <th>时长(分)</th>
              <th>消耗(kcal)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in historyRecords" :key="record.id">
              <td>{{ record.date }}</td>
              <td>{{ record.type }}</td>
              <td>{{ record.duration }}</td>
              <td class="highlight">{{ record.calories }}</td>
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
.data-section { display: flex; gap: 20px; }
.chart-card { flex: 1; }
.table-card { flex: 1; }
.record-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.record-table th, .record-table td { border-bottom: 1px solid #eee; padding: 10px; text-align: left; }
.highlight { color: #ff5722; font-weight: bold; }
</style>
