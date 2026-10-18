<script setup>
import { ref } from 'vue'

// 表单数据
const newRecord = ref({
  type: '跑步',
  duration: 30,
  intensity: '中等'
})

// 历史记录列表（假装有一些初始数据）
const historyRecords = ref([
  { id: 1, type: '跑步', duration: 30, intensity: '中等', calories: 300, date: '2026-10-15' }
])

// 添加记录的方法
const addRecord = () => {
  // 简单算法：根据运动类型和强度估算卡路里
  let baseRate = 10 // 跑步基础消耗
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

  alert('记录添加成功！')
}
</script>

<template>
  <div class="exercise-container">
    <h2>🏃 运动健身管理</h2>
    
    <!-- 打卡录入区 -->
    <div class="card">
      <h3>记录今日运动</h3>
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

    <!-- 历史记录展示区 -->
    <div class="card">
      <h3>运动打卡记录</h3>
      <table class="record-table">
        <thead>
          <tr>
            <th>日期</th>
            <th>运动类型</th>
            <th>时长(分钟)</th>
            <th>强度</th>
            <th>消耗(kcal)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in historyRecords" :key="record.id">
            <td>{{ record.date }}</td>
            <td>{{ record.type }}</td>
            <td>{{ record.duration }}</td>
            <td>{{ record.intensity }}</td>
            <td class="highlight">{{ record.calories }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
/* 简单的样式美化 */
.exercise-container { padding: 20px; max-width: 800px; margin: 0 auto; font-family: sans-serif; }
.card { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.form-group { margin-bottom: 15px; }
.form-group label { display: inline-block; width: 120px; }
.form-group input, .form-group select { padding: 6px; width: 200px; border: 1px solid #ccc; border-radius: 4px; }
.submit-btn { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
.submit-btn:hover { background: #45a049; }
.record-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.record-table th, .record-table td { border-bottom: 1px solid #eee; padding: 10px; text-align: left; }
.highlight { color: #ff5722; font-weight: bold; }
</style>
