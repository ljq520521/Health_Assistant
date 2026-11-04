<script setup>
import { feedbackStates, formatPercent } from './weeklyPlanUI.js'
defineProps({ stats: { type: Object, required: true } })
</script>
<template>
  <section class="weekly-stats" aria-label="一周执行统计">
    <div class="weekly-progress-heading"><strong>一周反馈进度</strong><span>{{ formatPercent(stats.feedback_progress_percent) }}</span></div>
    <progress :value="stats.feedback_progress_percent ?? 0" max="100" aria-label="一周反馈进度"></progress>
    <p class="recipe-note">可执行 {{ stats.actionable_slots }} 项 · 已反馈 {{ stats.answered_count }} 项 · 未反馈天数 {{ stats.pending_days }} 天 · 完全未反馈 {{ stats.days_without_any_feedback }} 天</p>
    <div class="weekly-metrics">
      <div><span>已反馈事项完成率</span><strong>{{ formatPercent(stats.completion_rate_percent) }}</strong><small>统计分母 {{ stats.completion_denominator }} 项；未反馈及不适用不计入</small></div>
      <div><span>部分完成</span><strong>{{ stats.counts?.partial ?? 0 }} 项</strong><small>单独统计，不作为全部完成</small></div>
    </div>
    <ul class="weekly-legend"><li v-for="(state, key) in feedbackStates" :key="key" :class="state.tone">{{ state.icon }} {{ state.label }} {{ stats.counts?.[key] ?? 0 }}</li></ul>
    <p class="recipe-note">无候选餐次不计为执行失败。完成反馈不会自动新增饮食记录，也不会扣减库存。</p>
  </section>
</template>
<style scoped>
.weekly-stats{padding:16px;background:#f1f7f2;border-radius:10px;margin:16px 0}.weekly-progress-heading{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:14px}progress{width:100%;height:12px;margin-top:12px;accent-color:#246b58}.weekly-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.weekly-metrics span,.weekly-metrics strong,.weekly-metrics small{display:block;overflow-wrap:anywhere}.weekly-metrics span{font-size:12px}.weekly-metrics strong{font-size:23px;margin:8px 0;color:#246b58}.weekly-metrics small{font-size:12px;line-height:1.6;color:#64796d}.weekly-legend{display:flex;gap:8px;flex-wrap:wrap;list-style:none;padding:0;font-size:12px}.weekly-legend li{padding:5px 8px;border-radius:5px}.success{background:#dcf0df;color:#185b2e}.danger{background:#ffe4df;color:#983629}.partial{background:#fff0d5;color:#845616}.neutral{background:#e7ece8;color:#526358}@media(max-width:390px){.weekly-metrics{grid-template-columns:1fr}.weekly-stats{padding:12px}}
</style>
