import test from 'node:test'
import assert from 'node:assert/strict'
import {reactive} from 'vue'
import {intakeText,goalText,ratioText,measurement,bucketDays,waterMetric} from './metricPresentation.js'
import {useAppliedQuery} from './analysisQuery.js'
import {chartGeometry,pointDescription,shortDate} from './chartPresentation.js'

test('真实0保留单位，未知和无记录不附单位',()=>{
  assert.equal(measurement(0,'g'),'0 g')
  assert.equal(measurement(null,'g'),'营养数据未知')
  assert.equal(intakeText({known_sum:null,data_status:'unknown'},'kcal'),'营养数据未知')
  assert.equal(intakeText({known_sum:null,data_status:'no_records'},'kcal'),'当天没有记录')
  assert.equal(intakeText({known_sum:null,data_status:'no_records'},'kcal',7),'区间没有记录')
  assert.equal(intakeText({known_sum:0,data_status:'partial'},'kcal',7),'0 kcal')
})
test('目标未设置与区间目标不完整分别展示，比例可大于100%',()=>{
  assert.equal(goalText({target:null,target_missing_days:7},'g',7),'目标未设置')
  assert.equal(goalText({target:null,target_missing_days:2},'g',7),'区间目标不完整')
  assert.equal(goalText({target:100,target_missing_days:0},'g',7),'100 g')
  assert.equal(ratioText({target:100,achievement_percent:0}),'0%')
  assert.equal(ratioText({target:100,achievement_percent:150}),'150%')
  assert.equal(ratioText({target:null,target_missing_days:2,achievement_percent:null},7),'区间目标不完整')
  assert.equal(ratioText({target:100,known_sum:null,data_status:'unknown',achievement_percent:null}),'营养数据未知')
})
test('饮水无记录不表示真实0，适配不改变后端字段',()=>{
  const source={known_sum_ml:null,target_ml:null,data_status:'no_records',target_missing_days:1}
  const before=JSON.stringify(source)
  assert.equal(intakeText(waterMetric(source),'ml'),'当天没有记录')
  assert.equal(goalText(waterMetric(source),'ml'),'目标未设置')
  assert.equal(JSON.stringify(source),before)
  assert.equal(bucketDays({recorded_days:2,missing_days:5}),7)
})
test('查询条件编辑不改变已应用条件，成功接受后清除提示',()=>{
  const filters=reactive({date_from:'2026-10-01',date_to:'2026-10-15',group_by:'day'})
  const query=useAppliedQuery(filters);query.accept(query.capture())
  filters.group_by='week';assert.equal(query.changed.value,true)
  assert.equal(query.applied.value.group_by,'day')
  const sent=query.capture();filters.date_to='2026-10-16'
  query.accept(sent);assert.equal(query.changed.value,true)
  query.accept(query.capture());assert.equal(query.changed.value,false)
  filters.date_from='2026-10-02';assert.equal(query.changed.value,true)
  filters.date_from='2026-10-01';assert.equal(query.changed.value,false)
})
test('查询失败未接受新条件时仍保留旧结果条件',()=>{
  const filters=reactive({date_from:'2026-10-01',date_to:'2026-10-15',group_by:'day'})
  const query=useAppliedQuery(filters);query.accept(query.capture());filters.group_by='month'
  // A rejected HTTP request never calls accept().
  assert.equal(query.applied.value.group_by,'day');assert.equal(query.changed.value,true)
})
test('触屏图表缺失处断线，0在零刻度，纵轴包含中间刻度',()=>{
  const chart={kind:'line',points:[{label:'2026-10-01',value:0,status:'complete'},{label:'2026-10-02',value:null,status:'unknown'},{label:'2026-10-03',value:20,status:'partial'},{label:'2026-10-04',value:null,status:'no_records'}]}
  const before=JSON.stringify(chart),g=chartGeometry(chart,260)
  assert.equal(g.points[0].y,g.bottom);assert.equal(g.points[1].y,null)
  assert.deepEqual(g.segments.map(s=>s.map(p=>p.value)),[[0],[20]])
  assert.equal(g.ticks.length,3);assert.equal(g.ticks[1].value,10)
  assert.equal(JSON.stringify(chart),before)
  assert.match(pointDescription(g.points[0],'g'),/0 g/)
  assert.match(pointDescription(g.points[1],'g'),/营养数据未知/)
  assert.doesNotMatch(pointDescription(g.points[1],'g'),/未知 g/)
  assert.match(pointDescription(g.points[2],'g'),/统计数据不完整/)
  assert.match(pointDescription(g.points[3],'g'),/当天没有记录/)
})
test('短日期刻度与单日/全缺失/长区间图表保持有效',()=>{
  assert.equal(shortDate('2026-10-15'),'10/15');assert.equal(shortDate('早餐'),'早餐')
  for(const values of [[null],[0],Array(366).fill(null)]){
    const g=chartGeometry({kind:'line',points:values.map((value,i)=>({label:String(i),value}))},220)
    assert.ok(g.points.every(p=>Number.isFinite(p.x)&&p.x>=g.left&&p.x<=g.right))
    assert.ok(g.ticks.every(p=>Number.isFinite(p.y)))
  }
})
