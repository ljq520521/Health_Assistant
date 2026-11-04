<script setup>
import { computed, ref } from 'vue'
import { displayTime, downloadReport, hours } from '../../api/sleep'
const props = defineProps({ analysis: Object, profile: Object })
const busy = ref(false), error = ref('')
const stages = computed(() => {
  const records = props.analysis.records
  const known = records.filter(row => row.deep_minutes != null || row.light_minutes != null)
  return { known: known.length, deep: known.reduce((n, row) => n + (row.deep_minutes || 0), 0), light: known.reduce((n, row) => n + (row.light_minutes || 0), 0) }
})
async function download() { busy.value = true; error.value = ''; try { await downloadReport(props.analysis.period, props.analysis.date_to) } catch (e) { error.value = e.message } finally { busy.value = false } }
function print() { window.print() }
</script>
<template>
  <div class="sleep-report-actions"><p>报告基于当前选择的周期与最新记录生成。</p><div class="sleep-actions"><button class="button secondary" :disabled="busy" @click="download">{{ busy ? '正在导出…' : '下载 CSV' }}</button><button class="button primary" @click="print">打印 / 存为 PDF</button></div></div><p v-if="error" class="sleep-error" role="alert">{{ error }}</p>
  <article id="sleep-report" class="sleep-panel sleep-report"><div class="sleep-report-heading"><div><p class="eyebrow">SLEEP JOURNAL / REPORT</p><h2>{{ analysis.period === 'week' ? '7 天' : '30 天' }}睡眠分析报告</h2><p>{{ profile?.display_name || '本地健康档案' }} · {{ analysis.date_from }} 至 {{ analysis.date_to }}</p></div><span class="sleep-chip">个人作息记录</span></div><div class="sleep-report-metrics"><div><span>已记录日期平均时长</span><strong>{{ hours(analysis.summary.average_minutes) }}</strong></div><div><span>平均作息分</span><strong>{{ analysis.summary.average_score ?? '—' }}<small> / 100</small></strong></div><div><span>数据覆盖</span><strong>{{ analysis.summary.recorded_days }} / {{ analysis.summary.period_days }}<small> 天</small></strong></div></div>
    <h3>周期小结</h3><ul><li v-for="item in analysis.observations" :key="item">{{ item }}</li></ul><p v-if="analysis.summary.change_minutes != null">相比前一周期，平均时长{{ analysis.summary.change_minutes >= 0 ? '增加' : '减少' }} {{ Math.abs(analysis.summary.change_minutes) }} 分钟；前期有 {{ analysis.summary.previous_recorded_days }} 天记录。</p>
    <h3>手动睡眠阶段记录</h3><p v-if="stages.known">{{ stages.known }} / {{ analysis.records.length }} 条记录填写了至少一种阶段：已填深睡累计 {{ stages.deep }} 分钟，已填浅睡累计 {{ stages.light }} 分钟。未填写部分不推断，阶段合计不代表完整周期。</p><p v-else>尚无深浅睡记录，不生成阶段比例或睡眠周期结论。</p>
    <h3>记录明细</h3><table class="sleep-table"><thead><tr><th>醒来日期</th><th>时长</th><th>作息分</th><th>作息偏离提示</th></tr></thead><tbody><tr v-for="row in analysis.records" :key="row.id"><td>{{ row.wake_date }}</td><td>{{ hours(row.duration_minutes) }}</td><td>{{ row.score }}</td><td>{{ row.alerts.join('；') || '—' }}</td></tr><tr v-if="!analysis.records.length"><td colspan="4">本期暂无数据</td></tr></tbody></table><div class="sleep-report-foot"><p>{{ analysis.notice }}</p><p>评分按当前个人目标重新计算；没有记录的日期不计入平均时长。</p><p>生成时间：{{ displayTime(analysis.generated_at) }}（Asia/Shanghai）</p></div>
  </article>
</template>
