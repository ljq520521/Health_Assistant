import test from 'node:test'
import assert from 'node:assert/strict'
import { recipeSource } from './recipeSource.js'
import { useReminderDraft } from './reminderDraft.js'
import { reportCopy, demoReportNotice, DEMO_REPORT_NOTICE } from './reportCopy.js'
import { exportReportPDF, exportChartPNG } from './reportExport.js'
import { COURSE_APPROVAL_NOTICE } from './demoContext.js'
import { metrics, chartsFor } from './reportPresentation.js'

test('recipe sources retain pending/trial status but hide import identity and hashes',()=>{
  const r=Object.freeze({source_type:'user_entered',source_note:'项目团队自编，AI辅助草案，待审核；未经实际试做；营养按投料估算。\nHAIMPORT1:{"content_sha256":"abc","run_id":"x","key":"id"}',source_url:'https://example.org/recipe'})
  const s=recipeSource(r)
  assert.match(s.label,/项目团队自编/);assert.match(s.review,/待团队正式审核/);assert.equal(s.trial,'未经实际试做')
  assert.doesNotMatch(JSON.stringify(s),/HAIMPORT1|content_sha256|run_id|"key"/)
  assert.equal(s.href,r.source_url);assert.match(r.source_note,/HAIMPORT1/)
})
test('source marker alone never implies approval or a completed cooking trial',()=>{
  const s=recipeSource({source_note:'HAIMPORT1:{"approved":true}',source_url:'javascript:alert(1)'})
  assert.match(s.review,/未确认/);assert.equal(s.trial,'实际试做情况未提供');assert.equal(s.href,'')
})
const initial={enabled:false,mode:'interval',fixed_times:[],interval_minutes:60,active_start:'09:00',active_end:'18:00',pause_when_goal_met:true}
test('draft persists while other data is queried, cancel restores saved settings without a write',async()=>{
  let writes=0
  const d=useReminderDraft({get:async()=>structuredClone(initial),save:async()=>{writes++}})
  await d.load();assert.equal(d.dirty.value,false)
  d.settings.mode='fixed_times';d.fixedTimes.value=['09:00','11:00']
  await Promise.resolve({items:[]}) // record requests do not call draft.load
  assert.equal(d.dirty.value,true);assert.deepEqual(d.fixedTimes.value,['09:00','11:00'])
  d.cancel();assert.equal(d.settings.mode,'interval');assert.equal(d.dirty.value,false);assert.equal(writes,0)
})
test('successful reminder save updates baseline and normalizes fixed times',async()=>{
  let sent
  const d=useReminderDraft({get:async()=>structuredClone(initial),save:async v=>(sent=v,{...v})})
  await d.load();d.settings.mode='fixed_times';d.fixedTimes.value=['09:00','11:00'];d.settings.enabled=true
  await d.save();assert.deepEqual(sent.fixed_times,['09:00','11:00']);assert.equal(d.dirty.value,false)
  d.fixedTimes.value=['12:00'];d.cancel();assert.deepEqual(d.fixedTimes.value,['09:00','11:00']);assert.equal(d.settings.enabled,true)
})
test('failed save retains changes and does not replace saved baseline',async()=>{
  const d=useReminderDraft({get:async()=>structuredClone(initial),save:async()=>{throw Error('模拟失败')}})
  await d.load();d.settings.interval_minutes=90
  await assert.rejects(d.save(),/模拟失败/);assert.equal(d.settings.interval_minutes,90);assert.equal(d.dirty.value,true)
  d.cancel();assert.equal(d.settings.interval_minutes,60)
})
const demo={notice:'仅供演示',database_path:'test/demo.db',review_status:'pending_final_confirmation',approved:false}
test('demo marking requires explicit demo configuration, never profile identity',()=>{
  assert.equal(demoReportNotice(demo),DEMO_REPORT_NOTICE)
  assert.equal(demoReportNotice({...demo,approved:true}),DEMO_REPORT_NOTICE)
  for(const value of [null,undefined,{}, {profile_id:1}, {approved:false}, {...demo,environment:'production'}]) assert.equal(demoReportNotice(value),'')
})
function fixture(){
  const nutrients=Object.fromEntries(metrics.map(([key])=>[key,{known_sum:0,target:null,achievement_percent:null,data_status:'partial',unknown_count:1}]))
  return {period:'week',date_from:'2026-10-05',date_to:'2026-10-11',period_from:'2026-10-05',period_to:'2026-10-11',period_days:7,time_zone:'Asia/Shanghai',is_partial_period:false,
    overview:{record_count:1,recorded_days:1,missing_days:6,recorded_meal_slots:1},averages:{known_calories_per_recorded_day:0,known_calories_per_period_day:0,recorded_day_denominator:1,period_day_denominator:7,note:'仅基于已知记录'},
    nutrition:{total:{nutrients},daily:[{actual_from:'2026-10-05',nutrients}]},water:{known_sum_ml:null,target_ml:null,achievement_percent:null,target_missing_days:7,record_count:0,recorded_days:0,missing_days:7,daily:[{date:'2026-10-05',known_sum_ml:null,data_status:'no_records'}]},meal_distribution:[{label:'早餐',record_count:1}],
    suggestions:[{rule_id:'missing_diet_days',text:'有1天未记录饮食，不代表没有进食。',evidence:{path:'overview.missing_dates',dates:['2026-10-07']}},{rule_id:'unknown_calories_kcal',text:'有1条饮食记录未填写热量。',evidence:{path:'nutrition.total.nutrients.calories_kcal',unknown_count:1}},{rule_id:'target_calories_kcal',text:'已知热量记录比例为29.988888%。',evidence:{known_sum:599.77776,target:2000,data_status:'partial'}}],
    completeness_notes:['NULL表示未知；no_records表示无记录。'],schema_version:'diet-report-v1',generated_at:'2026-10-15T00:00:00Z'}
}
test('Chinese report evidence preserves distinctions and original statistics',()=>{
  const r=fixture(),before=JSON.stringify(r),copy=reportCopy(r)
  assert.match(copy.suggestions[0].evidence[0],/2026年10月7日没有饮食记录/)
  assert.match(copy.suggestions[1].evidence[0],/1条饮食记录未填写热量/)
  assert.match(copy.notes[0],/目标未设置/);assert.match(copy.notes[0],/营养数值未填写/);assert.match(copy.notes[0],/当天没有录入记录/)
  assert.doesNotMatch(JSON.stringify(copy),/nutrition\.total|missing_diet_days|NULL|no_records|"path"/)
  assert.equal(JSON.stringify(r),before)
})
test('PDF and PNG use shared Chinese copy; each demo PDF page and PNG is marked; normal exports are not',async t=>{
  const canvases=[]
  const old=globalThis.document
  globalThis.document={body:{append(){}},createElement(tag){
    if(tag==='a')return {click(){},remove(){}}
    const texts=[],ctx={fillRect(){},save(){},restore(){},translate(){},scale(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},arc(){},fill(){},fillText(s){texts.push(String(s))},measureText(s){return {width:[...s].length*12}}}
    const c={width:0,height:0,texts,getContext:()=>ctx,toBlob:(fn,type)=>fn(new Blob([new Uint8Array([255,216,255,217])],{type:type||'image/png'}))};canvases.push(c);return c
  }}
  try{
    const report=fixture(),before=JSON.stringify(report)
    const pdf=await exportReportPDF(report,{demo})
    assert.equal(pdf.blob.type,'application/pdf');assert.match(await pdf.blob.text(),/^%PDF-1.4/);assert.match(pdf.name,/2026-10-05_2026-10-11\.pdf$/)
    assert.ok(canvases.length>1)
    for(const c of canvases)assert.ok(c.texts.includes(DEMO_REPORT_NOTICE))
    const text=canvases.flatMap(c=>c.texts).join('\n')
    assert.match(text,/2026年10月7日没有饮食记录/);assert.match(text,/北京时间/);assert.match(text,/29.99%/)
    assert.doesNotMatch(text,/missing_diet_days|nutrition\.total|NULL|no_records|diet-report-v1|Asia\/Shanghai|29\.988888/)
    canvases.length=0;const png=await exportChartPNG(report,chartsFor(report)[0],{demo});assert.equal(png.blob.type,'image/png');assert.match(png.name,/\.png$/)
    assert.ok(canvases[0].texts.includes(DEMO_REPORT_NOTICE))
    const course={...demo,environment:'development_demo',approved:true,review_status:'approved',course_approval:{status:'approved',scope:'team_course_demonstration_only',manifest_sha256:'a'.repeat(64)}}
    const approvedNotice=`开发演示 · 非真实健康记录 · ${COURSE_APPROVAL_NOTICE}`
    canvases.length=0;await exportReportPDF(report,{demo:course})
    assert.ok(canvases.length>1)
    for(const c of canvases)assert.ok(c.texts.includes(approvedNotice))
    canvases.length=0;await exportChartPNG(report,chartsFor(report)[0],{demo:course})
    assert.ok(canvases[0].texts.includes(approvedNotice))
    canvases.length=0;await exportReportPDF(report);await exportChartPNG(report,chartsFor(report)[0])
    assert.equal(canvases.some(c=>c.texts.some(text=>text.includes('开发演示'))),false)
    assert.equal(JSON.stringify(report),before)
  }finally{if(old===undefined)delete globalThis.document;else globalThis.document=old}
})
