import {percentInText} from './metricPresentation.js'
import { metrics, format, statuses } from './reportPresentation.js'
import { isDevelopmentDemo, demoApprovalText } from './demoContext.js'

export const DEMO_REPORT_NOTICE = '开发演示 · 非真实健康记录 · 来源数据待正式审核'
// The object must originate from /api/diet/config.demo, never a profile or record flag.
export function demoReportNotice(demo) {
  return isDevelopmentDemo(demo)
    ? `开发演示 · 非真实健康记录 · ${demoApprovalText(demo)}` : ''
}
const dateLabel = value => /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.replace(/^(\d+)-(\d+)-(\d+)$/, (_,y,m,d)=>`${y}年${Number(m)}月${Number(d)}日`) : '日期未提供'
const meals = { breakfast:'早餐', lunch:'午餐', dinner:'晚餐', snack:'加餐' }
const names = Object.fromEntries(metrics.map(([key,label])=>[key,label]))
const units = Object.fromEntries(metrics.map(([key,,unit])=>[key,unit]))
function evidenceLines(s) {
  const e = s.evidence || {}, rule = s.rule_id
  if (rule === 'missing_diet_days' || rule === 'missing_water_days') return (e.dates || []).map(d=>`${dateLabel(d)}没有${rule === 'missing_diet_days' ? '饮食' : '饮水'}记录。`)
  if (rule?.startsWith('unknown_') && names[rule.slice(8)]) return [`本报告区间有${e.unknown_count}条饮食记录未填写${names[rule.slice(8)]}。未知数值不按0计算。`]
  if (rule?.startsWith('target_') && names[rule.slice(7)]) {
    const key = rule.slice(7)
    return [`已知${names[key]}累计${format(e.known_sum)} ${units[key]}；按日期生效的自设目标累计${format(e.target)} ${units[key]}。`, `${statuses[e.data_status] || '数据状态未提供'}；此比例只描述已记录数据，不判断实际摄入不足或过量。`]
  }
  if (rule === 'meal_distribution') return [Object.entries(meals).map(([key,label])=>`${label}${e.counts?.[key] ?? '未知'}条`).join('、')+'；按食物记录条数统计，不等于实际进餐次数。']
  if (rule === 'recorded_water_below_target') return (e.days || []).map(d=>`${dateLabel(d.date)}：已记录${format(d.recorded_ml)} ml，自设目标${format(d.target_ml)} ml，相差${format(d.gap_ml)} ml。记录可能不完整，不推断实际饮水不足。`)
  if (rule === 'water_target') return [`区间已记录饮水${format(e.known_sum_ml)} ml；按每天实际生效版本累计的饮水目标${format(e.target_ml)} ml。`, `${statuses[e.data_status] || '数据状态未提供'}；不推断实际饮水不足。`]
  return ['此项说明暂未提供中文依据，可在开发调试详情中核对原始数据。']
}
export function reportCopy(report) {
  return {
    suggestions:report.suggestions.map(s=>({ text:percentInText(s.text), evidence:evidenceLines(s) })),
    notes:report.completeness_notes.map(note=>note.includes('NULL') || note.includes('no_records')
      ? '0表示已填写数值确实为零；未知表示营养数值未填写；暂无记录表示当天没有录入记录。目标未设置或区间目标不完整时不计算目标比例。这些情况都不能等同于实际零摄入。' : note),
  }
}
