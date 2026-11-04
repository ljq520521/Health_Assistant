<script setup>
import { computed } from 'vue'
import { hours } from '../../api/sleep'
const props = defineProps({ analysis: Object })
const maxHours = computed(() => Math.max(10, ...props.analysis.daily.map(day => (day.duration_minutes || 0) / 60), props.analysis.settings.target_minutes / 60))
</script>
<template>
  <section class="sleep-panel" :class="{ 'sleep-chart-month': analysis.period === 'month' }"><div class="sleep-section-title"><div><h2>看见睡眠的节奏</h2><p>{{ analysis.date_from }} — {{ analysis.date_to }} · 按醒来日期汇总</p></div><span class="sleep-chip">目标 {{ hours(analysis.settings.target_minutes) }}</span></div>
    <div class="sleep-chart" role="img" :aria-label="`睡眠时长趋势，${analysis.summary.recorded_days} 天有记录，平均 ${hours(analysis.summary.average_minutes)}`"><div class="sleep-chart-label">{{ maxHours.toFixed(0) }} h</div><div class="sleep-chart-bars"><div class="sleep-goal-line" :style="{ bottom: `${analysis.settings.target_minutes / 60 / maxHours * 100}%` }"><span>目标</span></div><div v-for="day in analysis.daily" :key="day.date" class="sleep-chart-column"><div v-if="day.duration_minutes != null" class="sleep-bar" :class="{ reached: day.duration_minutes >= analysis.settings.target_minutes }" :style="{ height: `${day.duration_minutes / 60 / maxHours * 100}%` }" :title="`${day.date}：${hours(day.duration_minutes)}，${day.score} 分`" tabindex="0"><span>{{ hours(day.duration_minutes) }}</span></div><div v-else class="sleep-no-data" :title="`${day.date}：未记录`"></div><small>{{ day.date.slice(5).replace('-', '/') }}</small></div></div></div>
    <p class="sleep-muted">浅色表示未达到个人时长目标；缺失日期保留为空，不按 0 小时计算。变化对比前一个相同时长的周期。</p>
    <details class="sleep-details"><summary>查看每日明细与异常提示</summary><div class="sleep-table-wrap"><table class="sleep-table"><thead><tr><th>日期</th><th>累计时长</th><th>平均作息分</th><th>记录数</th></tr></thead><tbody><tr v-for="day in analysis.daily" :key="day.date"><td>{{ day.date }}</td><td>{{ hours(day.duration_minutes) }}</td><td>{{ day.score ?? '—' }}</td><td>{{ day.count }}</td></tr></tbody></table></div><ul class="sleep-alerts"><li v-for="row in analysis.records.filter(item => item.alerts.length)" :key="row.id">{{ row.wake_date }}：{{ row.alerts.join('；') }}</li></ul><p v-if="!analysis.summary.alert_count">本期没有触发作息偏离规则的记录。</p></details>
  </section>
</template>
