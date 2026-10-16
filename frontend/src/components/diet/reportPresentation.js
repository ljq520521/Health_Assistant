import {measurement,intakeText,waterMetric,statusText} from './metricPresentation.js'
// Presentation of server-calculated metrics only; no independent intake aggregation.
export const metrics=[['calories_kcal','热量','kcal'],['protein_g','蛋白质','g'],['fat_g','脂肪','g'],['carbohydrate_g','碳水化合物','g']]
export const periodLabels={day:'日报',week:'周报',month:'月报'}
export const statuses=statusText
export function format(value){return value==null?'未知 / 无可计算数据':new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(value)}
export function compact(value){return value==null?'—':Math.abs(value)>=1e7?value.toExponential(2):new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(value)}
export function reportName(r){return `饮食报告_${periodLabels[r.period]}_${r.date_from}_${r.date_to}`}
export function chartsFor(r){return [
  ...metrics.map(([key,label,unit])=>({id:key,title:`每日${label}已知摄入趋势`,unit,kind:'line',points:r.nutrition.daily.map(d=>({label:d.actual_from,value:d.nutrients[key].known_sum,status:d.nutrients[key].data_status})),note:'仅展示已知记录；未知或无记录处断线，橙色点表示数据不完整。'})),
  {id:'water',title:'每日已记录饮水趋势',unit:'ml',kind:'line',points:r.water.daily.map(w=>({label:w.date,value:w.known_sum_ml,status:w.data_status})),note:'无饮水记录处断线；暂无记录不代表实际没有饮水。'},
  {id:'meals',title:'餐次记录分布',unit:'条',kind:'bar',points:r.meal_distribution.map(m=>({label:m.label,value:m.record_count,status:'recorded'})),note:'按食物记录条数计算，不等于实际进餐次数。'}
]}
export function geometry(chart){
  const max=Math.max(1,...chart.points.filter(p=>p.value!=null).map(p=>p.value))
  const points=chart.points.map((p,i)=>({...p,x:chart.kind==='bar'?110+i*440/Math.max(1,chart.points.length-1):70+(chart.points.length===1?240:i/(chart.points.length-1)*480),y:p.value==null?null:190-p.value/max*135}))
  const segments=[];let current=[]
  for(const p of points){if(p.value==null){if(current.length)segments.push(current);current=[]}else current.push(p)}
  if(current.length)segments.push(current)
  return {max,points,segments}
}
export function overviewLines(r){return [
  `饮食记录 ${r.overview.record_count} 条；有记录 ${r.overview.recorded_days} / ${r.period_days} 天；无记录 ${r.overview.missing_days} 天`,
  `已登记餐次时段 ${r.overview.recorded_meal_slots} 个（按日期和餐次去重，不等于实际进餐次数）`,
  `已知热量 / 有记录天数：${measurement(r.averages.known_calories_per_recorded_day,'kcal/天',intakeText({known_sum:null,data_status:r.overview.record_count?'unknown':'no_records'},'',r.period_days))}（分母 ${r.averages.recorded_day_denominator} 天）`,
  `已知热量 / 区间天数：${measurement(r.averages.known_calories_per_period_day,'kcal/天',intakeText({known_sum:null,data_status:r.overview.record_count?'unknown':'no_records'},'',r.period_days))}（分母 ${r.averages.period_day_denominator} 天）`,
  `已记录饮水 ${intakeText(waterMetric(r.water),'ml',r.period_days)}；${r.water.record_count} 条；有记录 ${r.water.recorded_days} 天；无记录 ${r.water.missing_days} 天`
]}
