import test from 'node:test'
import assert from 'node:assert/strict'
import {timeZoneLabel,dateTimeText} from './displayTime.js'
import {percentText,percentInText,ratioText} from './metricPresentation.js'
import {preparationText} from './recipeUI.js'
import {normalizeFixedTimes,useReminderDraft} from './reminderDraft.js'
import {reportCopy} from './reportCopy.js'

test('UTC timestamps display in the configured zone across midnight without changing inputs',()=>{
  const timestamp='2026-10-14T16:05:00Z'
  assert.equal(dateTimeText(timestamp,'Asia/Shanghai'),'2026年10月15日 00:05')
  assert.equal(dateTimeText(timestamp,'UTC'),'2026年10月14日 16:05')
  assert.equal(timestamp,'2026-10-14T16:05:00Z')
  assert.equal(timeZoneLabel('Asia/Shanghai'),'北京时间')
  assert.equal(timeZoneLabel('UTC'),'UTC')
  assert.equal(dateTimeText(null,'Asia/Shanghai'),'时间未填写')
  assert.equal(dateTimeText('bad','Asia/Shanghai'),'时间无法显示')
  assert.equal(dateTimeText(timestamp,'bad-zone'),'时间无法显示')
})
test('percentage precision preserves zero, missing states and ratios above 100',()=>{
  assert.equal(percentText(0),'0%');assert.equal(percentText(125.6789),'125.68%')
  assert.equal(percentText(100),'100%');assert.equal(percentText(null),'未计算')
  assert.equal(percentText(NaN),'未计算')
  assert.equal(ratioText({target:null,achievement_percent:null,target_missing_days:1},7),'区间目标不完整')
  assert.equal(ratioText({target:null,achievement_percent:null}),'目标未设置')
  assert.equal(ratioText({target:100,achievement_percent:null,data_status:'no_records'}),'当天没有记录')
  assert.equal(ratioText({target:100,achievement_percent:null,known_sum:null,data_status:'unknown'}),'营养数据未知')
})
test('report and recommendation prose round only percentage display, never the supplied evidence',()=>{
  const report={suggestions:[{rule_id:'target_calories_kcal',text:'已记录比例为29.988888%，不是健康评分。',evidence:{known_sum:599.77776,target:2000,data_status:'partial'}}],completeness_notes:[]}
  const before=JSON.stringify(report)
  assert.equal(reportCopy(report).suggestions[0].text,'已记录比例为29.99%，不是健康评分。')
  assert.equal(percentInText('日期2026-10-15，100%与0%，库存12.345 g'),'日期2026-10-15，100%与0%，库存12.345 g')
  assert.equal(JSON.stringify(report),before)
})
test('recipe duration distinguishes missing from a recorded zero',()=>{
  assert.equal(preparationText(null),'制作时间未填写')
  assert.equal(preparationText(0),'制作时间 0 分钟')
  assert.equal(preparationText(15),'制作时间 15 分钟')
})
test('fixed times are strictly HH:mm, unique and ordered without mutating the draft',()=>{
  const times=['15:00','09:00','15:00','11:00']
  assert.deepEqual(normalizeFixedTimes(times),['09:00','11:00','15:00'])
  assert.deepEqual(times,['15:00','09:00','15:00','11:00'])
  for (const invalid of [[],[''],['9:00'],['24:00'],['09:60'],['09'],['09:00:30'],[null],null]) assert.throws(()=>normalizeFixedTimes(invalid))
})
const baseline={enabled:false,mode:'fixed_times',fixed_times:['09:00','11:00'],interval_minutes:60,active_start:'09:00',active_end:'18:00',pause_when_goal_met:true}
test('time rows support add/remove, cancel, sorted deduplicated save and a new saved baseline',async()=>{
  let sent
  const draft=useReminderDraft({get:async()=>structuredClone(baseline),save:async v=>(sent=structuredClone(v),v)})
  await draft.load();draft.fixedTimes.value.splice(0,1);draft.fixedTimes.value.push('15:00')
  assert.equal(draft.dirty.value,true);draft.cancel()
  assert.deepEqual(draft.fixedTimes.value,['09:00','11:00'])
  draft.fixedTimes.value=['15:00','09:00','15:00'];assert.equal(draft.hasDuplicates.value,true)
  await draft.save();assert.deepEqual(sent.fixed_times,['09:00','15:00'])
  assert.equal(draft.dirty.value,false);assert.equal(draft.hasDuplicates.value,false)
  draft.fixedTimes.value[0]='10:00';draft.cancel();assert.deepEqual(draft.fixedTimes.value,['09:00','15:00'])
})
test('invalid fixed times never call the API and failure retains the editable draft',async()=>{
  let calls=0
  const draft=useReminderDraft({get:async()=>structuredClone(baseline),save:async()=>{calls++;throw Error('网络失败')}})
  await draft.load();draft.fixedTimes.value=['']
  await assert.rejects(draft.save(),/HH:mm/);assert.equal(calls,0)
  draft.fixedTimes.value=['15:00','09:00','15:00']
  await assert.rejects(draft.save(),/网络失败/)
  assert.deepEqual(draft.fixedTimes.value,['15:00','09:00','15:00']);assert.equal(draft.dirty.value,true)
  draft.cancel();assert.deepEqual(draft.fixedTimes.value,baseline.fixed_times)
})
test('interval mode is preserved and does not submit unfinished fixed time rows',async()=>{
  let sent
  const draft=useReminderDraft({get:async()=>structuredClone(baseline),save:async v=>(sent=v,v)})
  await draft.load();draft.fixedTimes.value=[''];draft.settings.mode='interval';draft.settings.interval_minutes=75
  await draft.save();assert.deepEqual(sent.fixed_times,[]);assert.equal(sent.interval_minutes,75)
  assert.equal(sent.mode,'interval');assert.equal(draft.dirty.value,false)
})
