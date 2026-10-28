<script setup>
import { computed } from 'vue'
import { formatMinutes, shortDate } from './exerciseStats.js'

const props = defineProps({
  points: { type: Array, required: true },
  unit: { type: String, default: '分钟' },
})

const max = computed(() => Math.max(1, ...props.points.map((point) => point.minutes)))
const total = computed(() => props.points.reduce((sum, point) => sum + point.minutes, 0))
const peak = computed(() => Math.max(0, ...props.points.map((point) => point.minutes)))
const peakDate = computed(() => props.points.find((point) => point.minutes === peak.value)?.date || '')
const ariaLabel = computed(() => {
  if (!props.points.length) return '暂无趋势数据'
  const first = props.points[0].date
  const last = props.points[props.points.length - 1].date
  return `${first} 至 ${last} 每日运动时长，共 ${formatMinutes(total.value)}，最高 ${formatMinutes(peak.value)}`
})

function barHeight(minutes) {
  if (!minutes) return '0%'
  return `${Math.max(2, (minutes / max.value) * 100)}%`
}
</script>

<template>
  <figure class="trend-chart" role="img" :aria-label="ariaLabel">
    <figcaption class="trend-caption">
      <span>合计 <strong>{{ formatMinutes(total) }}</strong></span>
      <span v-if="peak">最高 {{ formatMinutes(peak) }}（{{ peakDate }}）</span>
    </figcaption>
    <ol v-if="total > 0" class="trend-bars">
      <li v-for="point in points" :key="point.date" :class="{ empty: !point.minutes }">
        <span class="trend-value">{{ point.minutes || '' }}</span>
        <span class="trend-track">
          <span
            class="trend-bar"
            :style="{ height: barHeight(point.minutes) }"
            :title="`${point.date}：${point.minutes} ${unit}`"
          />
        </span>
        <span class="trend-label">{{ shortDate(point.date) }}</span>
      </li>
    </ol>
    <p v-else class="trend-empty">这段时间没有运动记录，新增一条后这里会显示每日时长趋势。</p>
  </figure>
</template>

<style scoped>
.trend-chart { margin: 0; }
.trend-caption { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 12px; color: #74836d; margin-bottom: 14px; }
.trend-caption strong { color: var(--green); font-size: 14px; }
.trend-bars { display: flex; align-items: stretch; gap: 8px; height: 220px; margin: 0; padding: 0; list-style: none; }
.trend-bars li { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: flex-end; gap: 6px; }
.trend-value { height: 16px; font-size: 11px; color: #6d7f6a; text-align: center; font-variant-numeric: tabular-nums; }
.trend-track { flex: 1; display: flex; align-items: flex-end; border-bottom: 1px solid #e3ebdf; }
.trend-bar { display: block; width: 100%; border-radius: 5px 5px 0 0; background: linear-gradient(180deg, #6c9a86, #3f7a63); transition: height .25s ease; }
.trend-bars li.empty .trend-bar { height: 0 !important; }
.trend-bars li.empty .trend-track { position: relative; }
.trend-bars li.empty .trend-track::after { content: ''; position: absolute; inset: auto 0 0; height: 2px; background: #e3ebdf; border-radius: 2px; }
.trend-label { font-size: 10px; color: #8b968a; text-align: center; white-space: nowrap; }
.trend-empty { margin: 0; padding: 38px 20px; border: 1px dashed #d7e2d0; border-radius: 10px; text-align: center; font-size: 13px; color: #7b8975; }
@media (max-width: 700px) {
  .trend-bars { height: 170px; gap: 4px; }
  .trend-bars li:nth-child(even) .trend-label { visibility: hidden; }
  .trend-value { font-size: 10px; }
}
@media (prefers-reduced-motion: reduce) { .trend-bar { transition: none; } }
</style>
