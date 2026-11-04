// Display only: never replace missing measurements with zero or aggregate intake.
export const statusText = {complete:'已录入数据完整', partial:'统计数据不完整', unknown:'营养数据未知', no_records:'当天没有记录', recorded:'有已录入数据'}
export const numeric = value => typeof value === 'number' && Number.isFinite(value)
export const numberText = value => numeric(value) ? new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(value) : '营养数据未知'
export const percentText = (value, missing='未计算') => numeric(value) ? numberText(value)+'%' : missing
// Backend narrative stays intact apart from the precision of displayed percentages.
export const percentInText = text => String(text).replace(/(-?\d+(?:\.\d+)?)%/g, (_,value) => percentText(Number(value)))
export function measurement(value, unit, missing='营养数据未知') {
  return numeric(value) ? `${numberText(value)}${unit ? ' '+unit : ''}` : missing
}
export function intakeText(metric, unit, days=1) {
  if (metric?.data_status==='no_records') return days===1 ? '当天没有记录' : '区间没有记录'
  return measurement(metric?.known_sum,unit)
}
export function goalText(metric,unit,days=1) {
  if(numeric(metric?.target)) return measurement(metric.target,unit)
  return metric?.target_missing_days>0 && metric.target_missing_days<days ? '区间目标不完整' : '目标未设置'
}
export function ratioText(metric,days=1) {
  if(numeric(metric?.achievement_percent)) return percentText(metric.achievement_percent)
  if(!numeric(metric?.target)) return goalText(metric,'',days)
  return intakeText(metric,'',days)
}
export const bucketDays = bucket => (bucket?.recorded_days ?? 0)+(bucket?.missing_days ?? 0) || 1
export const waterMetric = water => ({...water,known_sum:water.known_sum_ml,target:water.target_ml})

export const completenessText = (metric,days=1) => metric?.data_status==='no_records' && days>1 ? '区间没有记录' : statusText[metric?.data_status] || '数据状态未提供'
